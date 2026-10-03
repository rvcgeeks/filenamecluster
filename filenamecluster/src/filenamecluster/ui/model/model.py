"""Session state for one window. Widgets live in the view.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from datetime import date
from pathlib import Path

from filenamecluster.core import (
    LIMIT_FIELDS,
    ClusterResult,
    ModelOptions,
    OptionError,
    TimestampPatterns,
    TimestampedFile,
    is_cluster_folder_name,
    rule_error,
)
from filenamecluster.log import trace_module
from .display import (
    ChooseStatus,
    OptionProblemStatus,
    PreviewStaysStatus,
    ReadFailureStatus,
    SummaryStatus,
    Topic,
    ValueProblemStatus,
)
from .notes import FolderNoteBook
from .options import OptionFields
from .patterns import PatternRow, PatternSnapshot
from .preview_facts import PreviewFacts


class AppModel(PreviewFacts):
    """All observable application state for one window."""

    def __init__(self) -> None:
        self._directory: Path | None = None
        self._result: ClusterResult | None = None
        self._selected_cluster: int | None = None
        self._selected_day: date | None = None
        self._files_by_day: dict[date, list[tuple[TimestampedFile, int]]] = {}
        self._option_text: dict[str, str] = {}
        self._limit_text: dict[str, str] = {}
        self._rows: list[PatternRow] = []
        self.custom_seq = 1
        self.language = "en"
        self.logging_enabled = False
        self.busy = False
        self.cluster_sort: tuple[str, bool] | None = None
        self.folder_notes = FolderNoteBook()
        self.apply_enabled = False
        self.flatten_enabled = False
        self._status = ChooseStatus()
        self._listeners: list[Callable[[Topic], None]] = []
        self._load_builtin()

    @property
    def directory(self) -> Path | None:
        return self._directory

    @property
    def result(self) -> ClusterResult | None:
        return self._result

    @property
    def selected_cluster(self) -> int | None:
        return self._selected_cluster

    @property
    def selected_day(self) -> date | None:
        return self._selected_day

    @property
    def files_by_day(self):
        return {day: list(entries) for day, entries in self._files_by_day.items()}

    @property
    def option_text(self) -> dict[str, str]:
        return dict(self._option_text)

    @property
    def limit_text(self) -> dict[str, str]:
        return dict(self._limit_text)

    @property
    def rows(self) -> tuple[PatternSnapshot, ...]:
        return self.pattern_rows()

    @property
    def status(self):
        return self._status

    def listen(self, callback: Callable[[Topic], None]) -> None:
        """Call ``callback`` with a topic after a later change. Not during setup."""

        self._listeners.append(callback)

    def set_directory(self, path: Path) -> None:
        self._directory = Path(path)
        self._notify(Topic.FOLDER)

    def reset_builtin(self) -> None:
        """Put the built-in options back and tell listeners."""

        self._load_builtin()
        self._notify(Topic.OPTIONS)

    def apply_saved(self, options: ModelOptions) -> None:
        builtin = {rule.key: rule.description for rule in TimestampPatterns().rules}
        self._option_text = {
            "floor": str(float(options.floor_hours)),
            "ceiling": str(float(options.ceiling_hours)),
        }
        self._limit_text = {
            key: str(int(getattr(options, key))) for key, *_rest in LIMIT_FIELDS
        }
        rows: list[PatternRow] = []
        seq = 1
        for key, description, pattern in options.rules:
            if key:
                iid = key
                dirty = description != builtin.get(key, description)
            else:
                iid = f"custom-{seq}"
                seq += 1
                dirty = False
            rows.append(PatternRow(iid, key, description, pattern, dirty))
        self._rows = rows
        self.custom_seq = seq
        self._notify(Topic.OPTIONS)

    def set_option_text(self, key: str, text: str) -> None:
        """Remember safety-limit text as the user types it. The widget already shows it."""

        self._option_text[key] = text
        self._notify(Topic.DRAFT)

    def set_limit_text(self, key: str, text: str) -> None:
        """Remember a year or priority as the user types it."""

        self._limit_text[key] = text
        self._notify(Topic.DRAFT)

    def option_drafts(self) -> dict[str, str]:
        return dict(self._option_text)

    def limit_drafts(self) -> dict[str, str]:
        return dict(self._limit_text)

    def pattern_rows(self) -> tuple[PatternSnapshot, ...]:
        return tuple(
            PatternSnapshot(row.iid, row.key, row.description, row.pattern, row.dirty, row.invalid)
            for row in self._rows
        )

    def pattern_table(self) -> list[tuple[str, str, str, str, bool]]:
        return [
            (row.iid, row.key, row.description, row.pattern, row.dirty) for row in self._rows
        ]

    def update_cell(self, iid: str, column: str, value: str) -> None:
        builtin = {rule.key: rule.description for rule in TimestampPatterns().rules}
        for row in self._rows:
            if row.iid != iid:
                continue
            if column == "description":
                row.description = value
                row.dirty = bool(row.key) and value != builtin.get(row.key, value)
            elif column == "pattern":
                row.pattern = value
            row.invalid = bool(rule_error(row.description, row.pattern))
            self._notify(Topic.PATTERNS)
            return

    def add_custom(self, description: str) -> str:
        iid = f"custom-{self.custom_seq}"
        self.custom_seq += 1
        self._rows.append(PatternRow(iid, "", description, "", False))
        self._notify(Topic.PATTERNS)
        return iid

    def remove_rows(self, iids: list[str]) -> None:
        drop = set(iids)
        self._rows = [row for row in self._rows if row.iid not in drop]
        self._notify(Topic.PATTERNS)

    def remember_preview(self, result: ClusterResult, invalid_rows: int = 0) -> None:
        self._result = result
        self._selected_cluster = None
        self._selected_day = result.clusters[0].start.date() if result.clusters else None
        self._files_by_day = {}
        for index, cluster in enumerate(result.clusters):
            for item in cluster.files:
                self._files_by_day.setdefault(item.timestamp.date(), []).append((item, index))
        event_folders = sum(
            1 for name in result.ignored_directories if is_cluster_folder_name(name)
        )
        self.apply_enabled = bool(result.clusters)
        self.flatten_enabled = event_folders > 0
        self.folder_notes.seed(self._directory, result)
        self._status = SummaryStatus(
            events=len(result.clusters),
            files=result.file_count,
            missing=len(result.ignored_without_timestamp),
            event_folders=event_folders,
            other_folders=len(result.ignored_directories) - event_folders,
            learned=self.learned_summary(),
            left_out=invalid_rows,
        )
        self._notify(Topic.PREVIEW)

    def replace_folder_note(self, stamp: str, prefix: str, suffix: str) -> None:
        self.folder_notes.replace(stamp, prefix, suffix)
        self._notify(Topic.PREVIEW)

    def set_selection(self, cluster: int | None, day: date | None) -> None:
        self._selected_cluster = cluster
        self._selected_day = day
        self._notify(Topic.SELECTION)

    def show_choose(self) -> None:
        self._status = ChooseStatus()
        self._notify(Topic.STATUS)

    def show_option_problem(self, error: OptionError) -> None:
        self._status = OptionProblemStatus(error.fault, error.field, error.low, error.high)
        self._notify(Topic.STATUS)

    def show_value_problem(self, message: str) -> None:
        self._status = ValueProblemStatus(message)
        self._notify(Topic.STATUS)

    def show_read_failure(self, path: Path, error: BaseException) -> None:
        self._status = ReadFailureStatus(path, error)
        self._notify(Topic.STATUS)

    def set_actions_and_status(
        self,
        apply: bool,
        flatten: bool,
        status: PreviewStaysStatus,
    ) -> None:
        """Set the action buttons and the following status together."""

        self.apply_enabled = bool(apply)
        self.flatten_enabled = bool(flatten)
        self._status = status
        self._notify(Topic.ACTIONS)

    def set_language(self, code: str) -> None:
        self.language = code
        self._notify(Topic.LANGUAGE)

    def set_logging(self, enabled: bool) -> None:
        self.logging_enabled = bool(enabled)
        self._notify(Topic.LOGGING)

    def set_busy(self, busy: bool) -> None:
        self.busy = bool(busy)
        self._notify(Topic.BUSY)

    def toggle_sort(self, column: str) -> tuple[str, bool]:
        current = self.cluster_sort
        descending = bool(current is not None and current[0] == column and not current[1])
        self.cluster_sort = (column, descending)
        self._notify(Topic.SORT)
        return self.cluster_sort

    def _load_builtin(self) -> None:
        patterns = TimestampPatterns()
        self._option_text = {
            "floor": str(OptionFields.hours(OptionFields.DEFAULTS.floor)),
            "ceiling": str(OptionFields.hours(OptionFields.DEFAULTS.ceiling)),
        }
        self._limit_text = {
            key: str(int(getattr(patterns, key))) for key, *_rest in LIMIT_FIELDS
        }
        self._rows = [
            PatternRow(rule.key, rule.key, rule.description, rule.pattern, False)
            for rule in patterns.rules
        ]
        self.custom_seq = 1

    def _notify(self, topic: Topic) -> None:
        for callback in list(self._listeners):
            callback(topic)


trace_module(sys.modules[__name__])
