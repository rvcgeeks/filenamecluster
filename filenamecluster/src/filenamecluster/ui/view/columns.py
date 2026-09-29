"""Keep the three Options columns the same width until the user drags a sash.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import sys
import tkinter as tk

from filenamecluster.log import trace_module


class EqualColumns:
    """Split ``options_columns`` into three even panes, and respect a user drag."""

    def __init__(self, host) -> None:
        self.host = host

    def mark_user_sized(self, event: tk.Event) -> None:
        """A sash drag should stick. Later window resizes must not snap it back."""

        if self.host.placing_columns or self.host.options_columns.winfo_width() < 200:
            return
        for index in range(2):
            sash_x, _sash_y = self.host.options_columns.sash_coord(index)
            if abs(event.x - sash_x) <= 8:
                self.host.options_user_sized = True
                return

    def balance(self, event: tk.Event) -> None:
        """Keep scheduling an even split until the row has its real width."""

        if self.host.options_user_sized or self.host.placing_columns or event.width < 200:
            return
        if self.host.equal_columns_job is not None:
            return
        self.host.equal_columns_job = self.host.root.after_idle(self.host.finish_equal_columns)

    def finish(self) -> None:
        self.host.equal_columns_job = None
        if self.host.options_user_sized:
            return
        width = self.host.options_columns.winfo_width()
        if width < 200:
            return
        self.place(width)

    def place(self, width: int) -> None:
        columns = self.host.options_columns
        actual = columns.winfo_width()
        if actual >= 200:
            width = actual
        sash = int(columns.cget("sashwidth"))
        pane = max((width - 2 * sash) // 3, 1)
        target = pane * 2 + sash
        try:
            current = columns.sash_coord(0)[0]
            following = columns.sash_coord(1)[0]
        except tk.TclError:
            current = following = -1
        if abs(current - pane) < 3 and abs(following - target) < 3:
            return
        self.host.placing_columns = True
        try:
            for child in columns.panes():
                columns.paneconfigure(child, width=pane)
            columns.sash_place(0, pane, 1)
            columns.sash_place(1, target, 1)
        finally:
            self.host.placing_columns = False


trace_module(sys.modules[__name__])
