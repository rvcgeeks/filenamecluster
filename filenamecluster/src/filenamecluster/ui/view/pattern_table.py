"""The filename-pattern table on the Options tab.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import sys
import tkinter as tk
from tkinter import ttk

from filenamecluster.log import trace_module
from . import theme

INVALID_TAG = "invalid"


class PatternTable:
    """Edit pattern cells in place, paint unusable rows orange, and report Validate clicks."""

    def __init__(self, host, kit) -> None:
        self.host = host
        self.kit = kit
        self._pattern_editor: ttk.Entry | None = None

    def build(self, rows: tk.PanedWindow) -> None:
        patterns = self.kit.text(ttk.LabelFrame(rows, padding=8), "patterns_frame")
        self.kit.flowing_help(patterns, "patterns_help")
        self.pattern_tree = self.kit.tree(
            patterns,
            (
                ("description", "col_description", 180, "w"),
                ("pattern", "col_pattern", 420, "w"),
                ("validate", "col_validate", 90, "center"),
            ),
        )
        self.pattern_tree.configure(height=6)
        self.pattern_tree.tag_configure(
            INVALID_TAG, background=theme.SELECTED_FILL, foreground=theme.TEXT
        )
        self.pattern_tree.bind("<Double-1>", self._edit_cell)
        self.pattern_tree.bind("<ButtonRelease-1>", self._validate_clicked, add="+")
        pattern_buttons = ttk.Frame(patterns)
        pattern_buttons.pack(anchor="w", pady=(6, 0))
        self.kit.text(
            ttk.Button(pattern_buttons, command=self.host.request_add_pattern), "add_pattern"
        ).pack(side="left")
        self.kit.text(
            ttk.Button(pattern_buttons, command=self.host.request_remove_pattern),
            "remove_pattern",
        ).pack(side="left", padx=8)
        rows.add(patterns, stretch="always", minsize=160)

    def flush_edits(self) -> None:
        """Commit an open cell editor into the session before a preview reads it."""

        self._close_editor(save=True)

    def selected_ids(self) -> list[str]:
        return [str(iid) for iid in self.pattern_tree.selection()]

    def show_rows(self, rows) -> None:
        """Draw pattern rows. Each row is ``(iid, key, description, pattern, dirty, invalid)``."""

        previous = set(self.pattern_tree.get_children())
        self._close_editor(save=False)
        self.pattern_tree.delete(*self.pattern_tree.get_children())
        fresh: list[str] = []
        for iid, key, description, pattern, dirty, invalid in rows:
            if not key and not description:
                text = self.host.translate("custom_pattern")
            elif not key or dirty:
                text = description
            else:
                text = self.host.translate(f"pattern_{key}")
            self.pattern_tree.insert(
                "",
                "end",
                iid=str(iid),
                values=(text, pattern, self.host.translate("col_validate")),
                tags=(INVALID_TAG,) if invalid else (),
            )
            if str(iid).startswith("custom-") and str(iid) not in previous and not pattern:
                fresh.append(str(iid))
        if len(fresh) == 1:
            self.begin_edit(fresh[0], "pattern")

    def marked(self, iid: str) -> bool:
        return INVALID_TAG in self.pattern_tree.item(iid, "tags")

    def validate(self, iid: str) -> None:
        """Report this row. The controller reads the stored expression."""

        self._close_editor(save=True)
        if self.host.actions is not None:
            self.host.actions.validate_row(iid)

    def begin_edit(self, iid: str, column: str) -> None:
        if self.host.inputs_locked:
            return
        self._close_editor(save=True)
        tree = self.pattern_tree
        bbox = tree.bbox(iid, column)
        if not bbox:
            return
        x, y, width, height = bbox
        entry = ttk.Entry(tree)
        entry.insert(0, self.host.actions.cell_text(iid, column))
        entry.select_range(0, "end")
        entry.place(x=x, y=y, width=max(width, 80), height=height)
        entry.focus_set()
        self._pattern_editor = entry

        def commit(_event: tk.Event | None = None) -> None:
            if self._pattern_editor is not entry:
                return
            self._pattern_editor = None
            value = entry.get()
            entry.destroy()
            if self.host.actions is not None:
                self.host.actions.pattern_committed(iid, column, value)

        def cancel(_event: tk.Event | None = None) -> str:
            if self._pattern_editor is entry:
                self._pattern_editor = None
                entry.destroy()
            return "break"

        entry.bind("<Return>", commit)
        entry.bind("<FocusOut>", commit)
        entry.bind("<Escape>", cancel)

    def _validate_clicked(self, event: tk.Event) -> None:
        if self.host.inputs_locked:
            return
        if self.pattern_tree.identify_column(event.x) != "#3":
            return
        row = self.pattern_tree.identify_row(event.y)
        if row:
            self.validate(row)

    def _edit_cell(self, event: tk.Event) -> None:
        if self.host.inputs_locked:
            return
        row = self.pattern_tree.identify_row(event.y)
        column = self.pattern_tree.identify_column(event.x)
        if not row or column not in {"#1", "#2"}:
            return
        name = self.pattern_tree["columns"][int(column[1:]) - 1]
        self.begin_edit(row, name)

    def _close_editor(self, save: bool) -> None:
        entry = self._pattern_editor
        if entry is None:
            return
        if save:
            entry.event_generate("<Return>")
            return
        self._pattern_editor = None
        entry.destroy()


trace_module(sys.modules[__name__])
