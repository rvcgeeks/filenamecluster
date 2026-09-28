"""Animated wait overlay shown while the folder is read or files are moved.

The window keeps handling events, so the operating system does not treat a
long scan or move as a frozen program. Buttons and option controls are
locked by the view for that time.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import sys
import time as clock
import tkinter as tk
from pathlib import Path
from tkinter import font as tkfont

from filenamecluster.log import trace_module
from filenamecluster.ui.view import theme

DEFAULT_DELAY_MS = 30
MIN_DELAY_MS = 16
WINDOWS_KEY = "#17324e"


def spinner_path() -> Path:
    """GIF played by ``SpinnerDialog``."""

    return Path(__file__).resolve().parents[1] / "assets" / "spinner.gif"


def gif_frames(path: Path) -> list[tk.PhotoImage]:
    """Every frame of a GIF. Tk's ``PhotoImage`` loads one index at a time."""

    frames: list[tk.PhotoImage] = []
    index = 0
    while index < 240:
        try:
            frames.append(tk.PhotoImage(file=str(path), format=f"gif -index {index}"))
        except tk.TclError:
            break
        index += 1
    return frames


def gif_delays(path: Path) -> list[int]:
    """Per-frame delay in milliseconds, read from each Graphic Control Extension.

    Tk does not expose these, and playing every frame at one fixed rate
    makes the animation run slow and jerky.
    """

    try:
        data = path.read_bytes()
    except OSError:
        return []
    if data[:3] != b"GIF" or len(data) < 13:
        return []
    delays: list[int] = []
    pending = DEFAULT_DELAY_MS
    pos = 13
    if data[10] & 0x80:
        pos += 3 * (2 ** ((data[10] & 7) + 1))
    try:
        while pos < len(data):
            block = data[pos]
            if block == 0x21:
                if data[pos + 1] == 0xF9:
                    centis = int.from_bytes(data[pos + 4 : pos + 6], "little")
                    pending = centis * 10 if centis else DEFAULT_DELAY_MS
                pos += 2
                while data[pos]:
                    pos += data[pos] + 1
                pos += 1
            elif block == 0x2C:
                packed = data[pos + 9]
                pos += 10
                if packed & 0x80:
                    pos += 3 * (2 ** ((packed & 7) + 1))
                pos += 1
                while data[pos]:
                    pos += data[pos] + 1
                pos += 1
                delays.append(max(pending, MIN_DELAY_MS))
                pending = DEFAULT_DELAY_MS
            else:
                break
    except IndexError:
        pass
    return delays


def _cached_frames(root: tk.Misc) -> tuple[list[tk.PhotoImage], list[int]]:
    """Decode the GIF once per window. Decoding every frame takes a visible moment."""

    owner = root.winfo_toplevel()
    cached = getattr(owner, "_filenamecluster_spinner", None)
    if cached is None:
        path = spinner_path()
        frames = gif_frames(path)
        delays = gif_delays(path)
        if len(delays) != len(frames):
            delays = [DEFAULT_DELAY_MS] * len(frames)
        cached = (frames, delays)
        owner._filenamecluster_spinner = cached
    return cached


def _overlay_background(top: tk.Toplevel) -> str:
    """Hide the title bar and make the empty part of the overlay see-through.

    On macOS an override-redirect window keeps an opaque backing, and
    ``systemTransparent`` is then drawn as a black box. An ``overlay``
    window has no title bar and honors ``-transparent``. ``ignoreClicks``
    lets the timeline and calendar behind the overlay still receive clicks.
    Windows uses a color key. Elsewhere the overlay keeps the plain window
    background, with no title bar.
    """

    system = str(top.tk.call("tk", "windowingsystem"))
    if system == "aqua":
        top.attributes("-transparent", True)
        try:
            top.tk.call(
                "::tk::unsupported::MacWindowStyle",
                "style",
                top,
                "overlay",
                "noShadow noActivates ignoreClicks",
            )
        except tk.TclError:
            top.overrideredirect(True)
        top.attributes("-transparent", True)
        return "systemTransparent"
    top.overrideredirect(True)
    if system == "win32":
        try:
            top.attributes("-transparentcolor", WINDOWS_KEY)
            return WINDOWS_KEY
        except tk.TclError:
            return theme.BACKGROUND
    return theme.BACKGROUND


class SpinnerDialog:
    """A borderless, see-through overlay that plays ``spinner.gif`` until ``close``."""

    def __init__(self, root: tk.Misc, message: str) -> None:
        self.frames, self.delays = _cached_frames(root)
        self.index = 0
        self._job: str | None = None
        self._due = 0.0
        self._root = root
        self.message = message
        top = tk.Toplevel(root)
        top.withdraw()
        top.resizable(False, False)
        top.protocol("WM_DELETE_WINDOW", lambda: None)
        self.top = top
        background = _overlay_background(top)
        top.configure(background=background, highlightthickness=0, borderwidth=0)
        base = tkfont.nametofont("TkDefaultFont")
        self.font = tkfont.Font(
            root=top,
            family=base.actual("family"),
            size=int(base.actual("size")) + 10,
            weight="bold",
        )
        self.canvas = tk.Canvas(
            top,
            background=background,
            highlightthickness=0,
            borderwidth=0,
        )
        self.canvas.pack()
        self.image_id: int | None = None
        self.text_id = self._draw(message)
        self._place()
        if str(root.state()) != "withdrawn":
            top.deiconify()
            shown = _overlay_background(top)
            top.configure(background=shown, highlightthickness=0, borderwidth=0)
            self.canvas.configure(background=shown)
            top.lift()
        self._play()

    def _draw(self, message: str) -> int:
        """Center the animation above the reason for this wait."""

        pad = theme.px(12)
        gap = theme.px(8)
        wrap = theme.px(520)
        frame = self.frames[0] if self.frames else None
        img_w = frame.width() if frame is not None else 0
        img_h = frame.height() if frame is not None else 0
        probe = self.canvas.create_text(
            0,
            0,
            anchor="nw",
            text=message,
            font=self.font,
            fill=theme.ACCENT_ACTIVE,
            width=wrap,
            justify="center",
        )
        left, top, right, bottom = self.canvas.bbox(probe)
        text_w = right - left
        text_h = bottom - top
        self.canvas.delete(probe)
        content_w = max(img_w, text_w, theme.px(160))
        total_w = content_w + pad * 2
        total_h = pad + img_h + (gap if img_h else 0) + text_h + pad
        self.canvas.configure(width=total_w, height=total_h)
        if frame is not None:
            self.image_id = self.canvas.create_image(total_w // 2, pad, anchor="n", image=frame)
        return self.canvas.create_text(
            total_w // 2,
            pad + img_h + (gap if img_h else 0),
            anchor="n",
            text=message,
            font=self.font,
            fill=theme.ACCENT_ACTIVE,
            width=wrap,
            justify="center",
        )

    def _place(self) -> None:
        root = self._root
        self.top.update_idletasks()
        width = self.top.winfo_reqwidth()
        height = self.top.winfo_reqheight()
        left = root.winfo_rootx() + max((root.winfo_width() - width) // 2, 0)
        top = root.winfo_rooty() + max((root.winfo_height() - height) // 2, 40)
        self.top.geometry(f"{width}x{height}+{left}+{top}")
        self.top.lift()

    def _play(self) -> None:
        """Advance on a steady clock so a late tick does not slow the loop down."""

        def advance() -> None:
            if not self.frames or not self.top.winfo_exists():
                return
            self.index = (self.index + 1) % len(self.frames)
            if self.image_id is not None:
                self.canvas.itemconfigure(self.image_id, image=self.frames[self.index])
            if self.index == 0:
                self.top.lift()
            now = clock.monotonic()
            self._due += self.delays[self.index] / 1000
            if self._due < now:
                self._due = now
            self._job = self.top.after(max(int((self._due - now) * 1000), 1), advance)

        self._due = clock.monotonic()
        advance()

    def close(self) -> None:
        job = self._job
        self._job = None
        if job is not None:
            try:
                self.top.after_cancel(job)
            except tk.TclError:
                pass
        try:
            self.top.destroy()
        except tk.TclError:
            pass


trace_module(sys.modules[__name__])
