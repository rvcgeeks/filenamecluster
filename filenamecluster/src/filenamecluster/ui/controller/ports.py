"""Ports the controller uses. The window implements them. Core does not.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from typing import Protocol, runtime_checkable

from filenamecluster.log import trace_module
from .requests import Notice, Question, Wait


@runtime_checkable
class DialogPort(Protocol):
    """Questions and one-way alerts. The view maps them to catalog text."""

    def tell(self, notice: Notice) -> None:
        """Show one alert."""

    def ask(self, question: Question) -> bool:
        """Ask a yes or no question."""


@runtime_checkable
class FolderPickerPort(Protocol):
    """Choose the root folder for a session."""

    def choose_directory(self, initial: Path) -> str:
        """Ask for a folder. An empty string means the user cancelled."""


@runtime_checkable
class TaskRunnerPort(Protocol):
    """Run one task while the view presents its progress."""

    def run_work(self, wait: Wait, work, on_done) -> None:
        """Run disk work under the spinner."""


class ViewPort(DialogPort, FolderPickerPort, TaskRunnerPort, Protocol):
    """The complete controller-facing surface of the window."""


@runtime_checkable
class DiskPort(Protocol):
    """Run one disk job and deliver its result on the UI thread."""

    def __call__(self, wait: Wait, work, on_done) -> None:
        """``on_done`` receives ``Success`` or ``Failure`` from ``AppController._run_disk``."""


@runtime_checkable
class LoggingPort(Protocol):
    """Apply the session's logging choice to the logging service."""

    def apply(self, enabled: bool) -> None:
        """Turn logging on or off. The model remains the source of the value."""


class ActionsPort(Protocol):
    """Actions a widget can report to the controller."""

    def choose_folder(self) -> None: ...
    def restore_defaults(self) -> None: ...
    def refresh(self, on_ready=None, wait: Wait = Wait.PREVIEW) -> None: ...
    def select_cluster(self, index: int | None, show_day: bool = True) -> None: ...
    def show_day(self, day: date) -> None: ...
    def cluster_selected(self, index: int) -> None: ...
    def day_chosen(self, day: date) -> None: ...
    def language_chosen(self, code: str) -> None: ...
    def logging_chosen(self, enabled: bool) -> None: ...
    def revise_option(self, key: str, text: str) -> None: ...
    def revise_limit(self, key: str, text: str) -> None: ...
    def sort_clusters(self, column: str) -> None: ...
    def pattern_committed(self, iid: str, column: str, value: str) -> None: ...
    def validate_row(self, iid: str) -> None: ...
    def cell_text(self, iid: str, column: str) -> str: ...
    def add_pattern_rule(self) -> None: ...
    def remove_pattern_rule(self, iids: list[str]) -> None: ...
    def apply_clustering(self) -> None: ...
    def flatten_clustering(self) -> None: ...
    def day_file_opened(self, row: int) -> None: ...
    def cluster_opened(self, index: int) -> None: ...
    def open_cluster_folder(self, index: int) -> None: ...


trace_module(sys.modules[__name__])
