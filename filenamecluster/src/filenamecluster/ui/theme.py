"""Light blue ttk theme shared by every widget in the app.

Author: Rajas Chavadekar (rvchavadekar@gmail.com). Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

BACKGROUND = "#eaf4fc"
SURFACE = "#ffffff"
PANEL = "#d4e8f7"
BORDER = "#a9cce3"
ACCENT = "#2e86c1"
ACCENT_ACTIVE = "#1f618d"
ACCENT_DISABLED = "#a9c9df"
TEXT = "#17324d"
MUTED = "#5d7a93"
ERROR = "#b03a2e"

BAR_FILLS = ("#85c1e9", "#5dade2")
BAR_OUTLINE = "#2874a6"
SELECTED_FILL = "#f5b041"
SELECTED_OUTLINE = "#b9770e"
GRID_MAJOR = "#a9cce3"
GRID_MINOR = "#e3f0fa"
FILE_MARK = "#2e86c1"


_LATIN_FAMILY: str | None = None
_SCRIPT_FACES: dict[str, tuple[str, ...]] = {
    "hi": (
        "Kohinoor Devanagari",
        "ITF Devanagari",
        "Devanagari MT",
        "Nirmala UI",
        "Noto Sans Devanagari",
        "Mukta",
        "Mangal",
    ),
    "ja": (
        "Hiragino Sans",
        "Hiragino Kaku Gothic ProN",
        "Hiragino Kaku Gothic Pro",
        "Yu Gothic",
        "YuGothic",
        "Noto Sans CJK JP",
        "Noto Sans JP",
        "Meiryo",
        "MS Gothic",
    ),
    "ko": (
        "Apple SD Gothic Neo",
        "AppleGothic",
        "NanumGothic",
        "Nanum Gothic",
        "Noto Sans CJK KR",
        "Noto Sans KR",
        "Malgun Gothic",
        "Gulim",
    ),
}
_SCRIPT_FACES["mr"] = _SCRIPT_FACES["hi"]


def use_script(root: tk.Misc, fonts: dict[str, tkfont.Font], code: str) -> None:
    """Use a face that can draw Hindi, Marathi, Japanese, or Korean."""

    global _LATIN_FAMILY
    base = tkfont.nametofont("TkDefaultFont")
    if _LATIN_FAMILY is None:
        _LATIN_FAMILY = str(base.cget("family"))
    family = _LATIN_FAMILY
    faces = _SCRIPT_FACES.get(code)
    if faces:
        available = set(tkfont.families(root))
        family = next((name for name in faces if name in available), _LATIN_FAMILY)
    base.configure(family=family)
    for font in fonts.values():
        font.configure(family=family)


def apply(root: tk.Misc) -> dict[str, tkfont.Font]:
    """Style ``root`` and return the extra fonts the app uses."""

    base = tkfont.nametofont("TkDefaultFont")
    fonts = {
        "title": base.copy(),
        "heading": base.copy(),
        "bold": base.copy(),
        "small": base.copy(),
    }
    size = abs(int(base.cget("size"))) or 12
    fonts["title"].configure(size=size + 8, weight="bold")
    fonts["heading"].configure(size=size + 3, weight="bold")
    fonts["bold"].configure(weight="bold")
    fonts["small"].configure(size=max(size - 2, 8))

    root.configure(background=BACKGROUND)
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(
        ".",
        background=BACKGROUND,
        foreground=TEXT,
        fieldbackground=SURFACE,
        bordercolor=BORDER,
        lightcolor=BACKGROUND,
        darkcolor=BORDER,
        troughcolor=BACKGROUND,
        focuscolor=ACCENT,
        selectbackground=ACCENT,
        selectforeground=SURFACE,
    )
    style.configure("TFrame", background=BACKGROUND)
    style.configure("Header.TFrame", background=PANEL)
    style.configure("TLabel", background=BACKGROUND, foreground=TEXT)
    style.configure("Header.TLabel", background=PANEL, foreground=TEXT)
    style.configure(
        "Title.TLabel", background=PANEL, foreground=ACCENT_ACTIVE, font=fonts["title"]
    )
    style.configure("Path.TLabel", background=PANEL, foreground=MUTED)
    style.configure("Muted.TLabel", foreground=MUTED)
    style.configure("Info.TLabel", foreground=ACCENT_ACTIVE, font=fonts["bold"])
    style.configure("Status.TLabel", background=PANEL, foreground=TEXT, padding=(10, 4))
    style.configure("Error.TLabel", background=PANEL, foreground=ERROR, padding=(10, 4))

    style.configure("TButton", background=SURFACE, padding=(12, 5), bordercolor=BORDER)
    style.map(
        "TButton",
        background=[("pressed", BORDER), ("active", PANEL)],
        foreground=[("disabled", MUTED)],
    )
    style.configure(
        "Accent.TButton",
        background=ACCENT,
        foreground=SURFACE,
        bordercolor=ACCENT_ACTIVE,
        font=fonts["bold"],
        padding=(16, 6),
    )
    style.map(
        "Accent.TButton",
        background=[
            ("disabled", ACCENT_DISABLED),
            ("pressed", ACCENT_ACTIVE),
            ("active", ACCENT_ACTIVE),
        ],
        foreground=[("disabled", SURFACE)],
    )

    style.configure("TLabelframe", background=BACKGROUND, bordercolor=BORDER)
    style.configure(
        "TLabelframe.Label",
        background=BACKGROUND,
        foreground=ACCENT_ACTIVE,
        font=fonts["bold"],
    )
    style.configure("TSpinbox", arrowcolor=ACCENT, fieldbackground=SURFACE)
    style.configure("TNotebook", background=BACKGROUND, bordercolor=BORDER)
    style.configure("TNotebook.Tab", background=PANEL, padding=(16, 6))
    style.map(
        "TNotebook.Tab",
        background=[("selected", SURFACE)],
        foreground=[("selected", ACCENT_ACTIVE)],
    )
    style.configure(
        "Treeview",
        background=SURFACE,
        fieldbackground=SURFACE,
        rowheight=24,
        bordercolor=BORDER,
    )
    style.configure("Treeview.Heading", background=PANEL, font=fonts["bold"])
    style.map(
        "Treeview",
        background=[("selected", ACCENT)],
        foreground=[("selected", SURFACE)],
    )
    style.configure(
        "TScrollbar", background=PANEL, arrowcolor=ACCENT, troughcolor=BACKGROUND
    )
    return fonts
