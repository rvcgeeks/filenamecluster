"""Questions and warnings. The controller asks; this class talks to Tk.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import sys
import tkinter as tk
from collections.abc import Callable
from pathlib import Path

from tkinter import filedialog, messagebox

from filenamecluster.log import log_call, trace_module
class Dialogs:
    """Folder picker and message boxes parented on one window."""

    _filedialog = filedialog
    _messagebox = messagebox

    def __init__(self, parent: tk.Misc, translate: Callable[..., str]) -> None:
        self._parent = parent
        self._translate = translate

    def choose_directory(self, initial: Path) -> str:
        """Return the chosen folder, or an empty string when the user cancels."""

        start = initial if initial.is_dir() else Path.cwd()
        log_call("tkinter.filedialog.askdirectory")
        chosen = type(self)._filedialog.askdirectory(
            parent=self._parent,
            title=self._translate("choose_title"),
            initialdir=start,
            mustexist=True,
        )
        return str(chosen) if chosen else ""

    def ask_yes_no(self, title: str, body: str) -> bool:
        log_call("tkinter.messagebox.askyesno")
        return bool(type(self)._messagebox.askyesno(title, body, parent=self._parent))

    def info(self, title: str, body: str) -> None:
        type(self)._messagebox.showinfo(title, body, parent=self._parent)

    def error(self, title: str, body: str) -> None:
        type(self)._messagebox.showerror(title, body, parent=self._parent)

    def warning(self, title: str, body: str) -> None:
        type(self)._messagebox.showwarning(title, body, parent=self._parent)


trace_module(sys.modules[__name__])
