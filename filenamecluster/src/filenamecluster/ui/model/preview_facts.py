"""What a finished preview means for the buttons, the status line, and the tables.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import json
import sys
from datetime import date

from filenamecluster.core.operations.organize import is_cluster_folder_name
from filenamecluster.log import trace_module
from .display import LearnedKind, LearnedSummary, SkippedReason, as_shown, cover_days

_LEARNED = ("within_hours", "between_hours", "boundary_hours", "separated")


class PreviewFacts:
    """Facts derived from the last preview. ``AppModel`` mixes this in.

    The view receives these values and translates them. It does not decide
    which folders are events.
    """

    def skipped(
        self,
    ) -> tuple[
        tuple[tuple[str, SkippedReason], ...],
        tuple[tuple[str, SkippedReason], ...],
    ]:
        """Folder rows and file rows with semantic reasons."""

        result = self.result
        if result is None:
            return (), ()
        folders = tuple(
            (
                name,
                SkippedReason.EVENT_FOLDER
                if is_cluster_folder_name(name)
                else SkippedReason.SUBFOLDER,
            )
            for name in result.ignored_directories
        )
        files = tuple(
            (name, SkippedReason.NO_TIMESTAMP)
            for name in result.ignored_without_timestamp
        )
        return folders, files

    def learned_cells(self) -> tuple[tuple[str, str | None], ...]:
        """Learned-model values as they appear in the file. ``None`` means not loaded yet."""

        if self.result is None:
            return tuple((key, None) for key in _LEARNED)
        learned = self.result.model
        if learned is None:
            return tuple((key, "null") for key in _LEARNED)
        cells = []
        for key in _LEARNED:
            if key == "separated":
                cells.append((key, "true" if learned.separated else "false"))
            else:
                cells.append((key, json.dumps(getattr(learned, key))))
        return tuple(cells)

    def learned_summary(self) -> LearnedSummary:
        """Copy the core learned model into presentation-neutral facts."""

        result = self.result
        if result is None or result.model is None:
            return LearnedSummary(LearnedKind.NONE)
        if not result.model.separated:
            return LearnedSummary(LearnedKind.ONE_GROUP)
        return LearnedSummary(LearnedKind.BOUNDARY, result.model.boundary_hours)

    def shown(self):
        """Events as draw values. The view does not receive core cluster objects."""

        return as_shown(self.result)

    @property
    def has_preview(self) -> bool:
        return self.result is not None

    def cluster_order(self) -> list[int]:
        """Indexes of the current events in the selected list order."""

        events = self.shown()
        order = list(range(len(events)))
        if self.cluster_sort is None:
            return order
        column, descending = self.cluster_sort

        def sort_key(index: int) -> tuple[int, int]:
            event = events[index]
            value = event.number if column == "number" else len(event.files)
            return (value, index)

        order.sort(key=sort_key, reverse=descending)
        return order

    def day_entries(self, day: date) -> list[tuple]:
        """Draw rows for one day: clock, filename, and event number."""

        events = self.shown()
        rows = []
        for item, index in self.files_by_day.get(day, []):
            number = events[index].number if 0 <= index < len(events) else index + 1
            rows.append((item.timestamp, item.name, number))
        return rows

    def day_file(self, row: int):
        """The scanned file and event index behind one Day-detail row."""

        if self.selected_day is None:
            return None
        entries = self.files_by_day.get(self.selected_day, [])
        if not 0 <= row < len(entries):
            return None
        return entries[row]

    def cluster_on_day(self, day: date) -> int | None:
        """The event that owns ``day``. A later event wins a shared day."""

        info = cover_days(self.shown()).get(day)
        if info is None:
            return None
        return info.cluster

    def calendar_days(self):
        """The complete calendar projection. Widgets do not recompute ownership."""

        return cover_days(self.shown())


trace_module(sys.modules[__name__])
