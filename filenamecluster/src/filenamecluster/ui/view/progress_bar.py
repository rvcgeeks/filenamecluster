"""A progress bar shown while a folder is read or files are moved.

Every folder read and every file move shows this dialog. The bar is
indeterminate until the job reports a total, then it fills to that total.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import sys
import tkinter as tk
from tkinter import ttk

from filenamecluster.log import trace_module
from . import theme


def release_wait(widget: tk.Misc) -> None:
    """Close the progress bar before a confirmation or an OK prompt.

    The bar stays up while the window paints. A question has to be readable
    on its own, so the prompt dismisses the bar before Tk shows it.
    """

    toplevel = getattr(widget, "winfo_toplevel", None)
    if toplevel is None:
        return
    try:
        owner = toplevel()
    except tk.TclError:
        return
    dialog = getattr(owner, "_filenamecluster_wait", None)
    if dialog is None:
        return
    owner._filenamecluster_wait = None
    dialog.close()


def bar_span(done: int, total: int) -> tuple[str, int, int]:
    """Progressbar mode, value, and maximum for one reading."""

    if total <= 0:
        return "indeterminate", 0, 100
    done = min(max(int(done), 0), int(total))
    return "determinate", done, int(total)


class ProgressDialog:
    """The wait window. ``show`` moves the bar. ``close`` removes the window."""

    def __init__(self, root: tk.Misc, message: str) -> None:
        self._root = root
        self._indeterminate = True
        top = tk.Toplevel(root)
        top.withdraw()
        top.title(message)
        top.transient(root)
        top.resizable(False, False)
        top.protocol("WM_DELETE_WINDOW", lambda: None)
        top.configure(background=theme.BACKGROUND)
        self.top = top
        frame = ttk.Frame(top, padding=theme.px(16))
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=message, wraplength=theme.px(420), justify="left").pack(anchor="w")
        self.bar = ttk.Progressbar(frame, mode="indeterminate", maximum=100, length=theme.px(360))
        self.bar.pack(fill="x", pady=(theme.px(12), theme.px(8)))
        self.count = ttk.Label(frame, text="")
        self.count.pack(anchor="w")
        self.bar.start(40)
        self._place()
        if str(root.state()) != "withdrawn":
            top.deiconify()
            top.lift()

    def show(self, done: int, total: int) -> None:
        """Move the bar to this reading. A withdrawn test window is left hidden."""

        if not self.top.winfo_exists():
            return
        mode, value, maximum = bar_span(done, total)
        if mode == "indeterminate":
            if not self._indeterminate:
                self.bar.configure(mode="indeterminate", maximum=maximum, value=0)
                self.bar.start(40)
                self._indeterminate = True
            self.count.configure(text="")
            return
        if self._indeterminate:
            self.bar.stop()
            self._indeterminate = False
        self.bar.configure(mode="determinate", maximum=maximum, value=value)
        self.count.configure(text=f"{value} / {maximum}")

    def _place(self) -> None:
        root = self._root
        self.top.update_idletasks()
        width = max(self.top.winfo_reqwidth(), theme.px(420))
        height = self.top.winfo_reqheight()
        left = root.winfo_rootx() + max((root.winfo_width() - width) // 2, 0)
        top = root.winfo_rooty() + max((root.winfo_height() - height) // 2, 40)
        self.top.geometry(f"{width}x{height}+{left}+{top}")

    def close(self) -> None:
        try:
            self.bar.stop()
        except tk.TclError:
            pass
        try:
            self.top.destroy()
        except tk.TclError:
            pass


trace_module(sys.modules[__name__])
