"""What the window does when the user edits the filename pattern table.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import sys

from filenamecluster.core import rule_error
from filenamecluster.log import trace_module
from .ports import DialogPort
from .requests import PatternBlank, PatternInvalid, PatternValid


class PatternEdits:
    """Stores pattern edits in the session. The window draws the result."""

    def __init__(self, model, ui: DialogPort) -> None:
        self._model = model
        self._ui = ui

    def pattern_committed(self, iid: str, column: str, value: str) -> None:
        self._model.update_cell(iid, column, value)

    def validate_pattern(self, description: str, source: str) -> None:
        """Ask the window to show the alert for one pattern row."""

        if not str(source).strip():
            self._ui.tell(PatternBlank())
            return
        error = rule_error(description, source)
        if error:
            self._ui.tell(PatternInvalid(error))
            return
        self._ui.tell(PatternValid(description.strip()))

    def add_pattern_rule(self) -> None:
        self._model.add_custom("")

    def remove_pattern_rule(self, iids: list[str]) -> None:
        self._model.remove_rows(iids)

    def cell_text(self, iid: str, column: str) -> str:
        """The stored text of one cell. The window may be showing a translation."""

        for row in self._model.pattern_rows():
            if row.iid == iid:
                return row.description if column == "description" else row.pattern
        return ""

    def validate_row(self, iid: str) -> None:
        for row in self._model.pattern_rows():
            if row.iid == iid:
                self.validate_pattern(row.description, row.pattern)
                return


trace_module(sys.modules[__name__])
