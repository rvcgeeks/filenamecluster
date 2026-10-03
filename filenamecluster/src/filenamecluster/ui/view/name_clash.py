"""Replace or skip, the way a file manager asks about one existing name.

The words arrive already translated. This class writes the click onto the
clash it was given and does not move a file.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import sys
import tkinter as tk
from tkinter import ttk

from filenamecluster.log import trace_module
from filenamecluster.ui.model import ClashChoice, NameClash
from . import theme
from .spinner import release_wait


class NameClashDialog:
    """One destination filename, two actions, and an optional apply-to-all box."""

    def __init__(
        self,
        parent: tk.Misc,
        clash: NameClash,
        *,
        title: str,
        body: str,
        replace: str,
        skip: str,
        everyone: str | None,
    ) -> None:
        self.clash = clash
        self.for_all = tk.BooleanVar(parent, False)
        self.shows_all = clash.count > 1 and everyone is not None
        window = tk.Toplevel(parent)
        window.title(title)
        window.transient(parent)
        window.resizable(False, False)
        window.configure(background=theme.BACKGROUND)
        window.protocol("WM_DELETE_WINDOW", self.cancel)
        window.bind("<Escape>", lambda _event: self.cancel())
        self.window = window

        frame = ttk.Frame(window, padding=theme.px(16))
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=body, wraplength=theme.px(420), justify="left").pack(
            anchor="w", pady=(0, theme.px(12))
        )
        ttk.Button(frame, text=replace, command=self.choose_replace).pack(fill="x", pady=(0, theme.px(6)))
        ttk.Button(frame, text=skip, command=self.choose_skip).pack(fill="x")
        if self.shows_all:
            ttk.Checkbutton(frame, text=everyone, variable=self.for_all).pack(
                anchor="w", pady=(theme.px(12), 0)
            )
        window.withdraw()

    def show(self) -> None:
        """Show the dialog and wait until the user chooses or closes it."""

        release_wait(self.window.master)
        window = self.window
        window.update_idletasks()
        parent = window.master
        width = window.winfo_reqwidth()
        height = window.winfo_reqheight()
        x = parent.winfo_rootx() + max(0, (parent.winfo_width() - width) // 2)
        y = parent.winfo_rooty() + max(0, (parent.winfo_height() - height) // 2)
        window.geometry(f"+{x}+{y}")
        window.deiconify()
        window.lift()
        window.focus_set()
        window.grab_set()
        window.wait_window()

    def choose_replace(self) -> None:
        self._choose(ClashChoice.REPLACE)

    def choose_skip(self) -> None:
        self._choose(ClashChoice.SKIP)

    def cancel(self) -> None:
        self.clash.cancelled = True
        self.clash.choice = None
        self.window.destroy()

    def _choose(self, choice: ClashChoice) -> None:
        self.clash.choice = choice
        self.clash.for_all = bool(self.for_all.get()) if self.shows_all else False
        self.clash.cancelled = False
        self.window.destroy()


trace_module(sys.modules[__name__])
