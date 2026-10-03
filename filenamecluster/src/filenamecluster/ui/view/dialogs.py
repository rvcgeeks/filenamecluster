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
from filenamecluster.ui.model import NameClash
from . import prompt
from .name_clash import NameClashDialog
from .spinner import release_wait

_ASK_YES_NO = messagebox.askyesno
_SHOW_INFO = messagebox.showinfo
_SHOW_ERROR = messagebox.showerror


class Dialogs:
    """Folder picker and message boxes parented on one window."""

    _filedialog = filedialog
    _messagebox = messagebox

    def __init__(self, parent: tk.Misc, translate: Callable[..., str]) -> None:
        self._parent = parent
        self._translate = translate

    def choose_directory(self, initial: Path, title_key: str = "choose_title") -> str:
        """Return the chosen folder, or an empty string when the user cancels."""

        start = initial if initial.is_dir() else Path.cwd()
        release_wait(self._parent)
        log_call("tkinter.filedialog.askdirectory")
        chosen = type(self)._filedialog.askdirectory(
            parent=self._parent,
            title=self._translate(title_key),
            initialdir=start,
            mustexist=True,
        )
        return str(chosen) if chosen else ""

    def ask_name_clash(
        self,
        clash: NameClash,
        *,
        title: str,
        body: str,
        replace: str,
        skip: str,
        everyone: str | None,
    ) -> None:
        """Show the replace-or-skip dialog and wait until it writes ``clash``."""

        release_wait(self._parent)
        NameClashDialog(
            self._parent,
            clash,
            title=title,
            body=body,
            replace=replace,
            skip=skip,
            everyone=everyone,
        ).show()

    def ask_yes_no(self, title: str, body: str) -> bool:
        """Ask during Apply or Flatten. The timer running out answers OK."""

        log_call("tkinter.messagebox.askyesno")
        release_wait(self._parent)
        box = type(self)._messagebox
        if box.askyesno is not _ASK_YES_NO:
            return bool(box.askyesno(title, body, parent=self._parent))
        return prompt.yes_no(
            self._parent,
            title,
            body,
            ok=self._translate("prompt_ok"),
            cancel=self._translate("prompt_cancel"),
            countdown=self._translate("prompt_countdown", seconds="{seconds}"),
            timeout=prompt.PROMPT_TIMEOUT_SECONDS,
        )

    def info(self, title: str, body: str, *, timed: bool = False) -> None:
        release_wait(self._parent)
        if self._timed(timed, "showinfo", _SHOW_INFO):
            prompt.yes_no(
                self._parent,
                title,
                body,
                ok=self._translate("prompt_ok"),
                cancel=None,
                countdown=self._translate("prompt_countdown", seconds="{seconds}"),
                timeout=prompt.PROMPT_TIMEOUT_SECONDS,
            )
            return
        type(self)._messagebox.showinfo(title, body, parent=self._parent)

    def error(self, title: str, body: str, *, timed: bool = False) -> None:
        release_wait(self._parent)
        if self._timed(timed, "showerror", _SHOW_ERROR):
            prompt.yes_no(
                self._parent,
                title,
                body,
                ok=self._translate("prompt_ok"),
                cancel=None,
                countdown=self._translate("prompt_countdown", seconds="{seconds}"),
                timeout=prompt.PROMPT_TIMEOUT_SECONDS,
            )
            return
        type(self)._messagebox.showerror(title, body, parent=self._parent)

    def _timed(self, timed: bool, name: str, original) -> bool:
        """A replaced messagebox is a test double and answers at once."""

        return timed and getattr(type(self)._messagebox, name) is original

    def warning(self, title: str, body: str) -> None:
        release_wait(self._parent)
        type(self)._messagebox.showwarning(title, body, parent=self._parent)


trace_module(sys.modules[__name__])
