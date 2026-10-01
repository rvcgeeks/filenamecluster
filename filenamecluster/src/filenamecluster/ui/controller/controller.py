"""What the window does when the user chooses a folder, previews, or edits options.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

from filenamecluster.log import event, trace_module
from filenamecluster.ui.model import AppModel
from .files import SystemFiles
from .logging import SystemLogging
from .opening import OpenActions
from .pattern_edits import PatternEdits
from .ports import DiskPort, LoggingPort, ViewPort
from .previewing import FolderPreviewing
from .relocation import FolderRelocation
from .requests import Failure, Success, Wait


class AppController:
    """Turns a user action into a call on the session or the folder workflow.

    ``ui`` asks a question, shows a dialog, chooses a folder, and runs disk
    work. This class does not name a widget, translate a sentence, or draw.
    It opens files with ``SystemFiles`` and applies the log switch with
    ``SystemLogging``. ``disk``, when given, runs folder work instead of
    ``ui.run_work``.
    """

    def __init__(
        self,
        model: AppModel,
        ui: ViewPort,
        disk: DiskPort | None = None,
        *,
        files: SystemFiles | None = None,
        logging: LoggingPort | None = None,
    ) -> None:
        self.model = model
        self.ui = ui
        self._disk = disk
        self._logging = SystemLogging() if logging is None else logging
        self._files = SystemFiles() if files is None else files
        self._previewing = FolderPreviewing(model, self._dispatch_disk)
        self._relocation = FolderRelocation(
            model,
            ui,
            self._dispatch_disk,
            self._previewing.refresh,
        )
        self._edits = PatternEdits(model, ui)
        self._opening = OpenActions(model, self._files, ui)

    def choose_folder(self) -> None:
        chosen = self.ui.choose_directory(Path.cwd() / "data")
        if chosen:
            self.load_folder(Path(chosen))

    def load_folder(self, folder: Path) -> None:
        self._previewing.load_folder(folder)

    def restore_defaults(self) -> None:
        event("defaults_restored")
        self.model.reset_builtin()
        self.refresh()

    def refresh(self, on_ready=None, wait: Wait = Wait.PREVIEW) -> None:
        """Re-scan the folder. Nothing is moved."""

        self._previewing.refresh(on_ready, wait)

    def select_cluster(self, index: int | None, show_day: bool = True) -> None:
        result = self.model.result
        if result is None or index is None or not 0 <= index < len(result.clusters):
            return
        day = result.clusters[index].start.date() if show_day else self.model.selected_day
        self.model.set_selection(index, day)

    def show_day(self, day: date) -> None:
        self.model.set_selection(self.model.selected_cluster, day)

    def cluster_selected(self, index: int) -> None:
        if index != self.model.selected_cluster:
            self.select_cluster(index)

    def day_chosen(self, day: date) -> None:
        index = self.model.cluster_on_day(day)
        if index is not None:
            self.model.set_selection(index, day)
            return
        self.model.set_selection(self.model.selected_cluster, day)

    def language_chosen(self, code: str) -> None:
        if code == self.model.language:
            return
        event("language_changed", language=code)
        self.model.set_language(code)

    def logging_chosen(self, enabled: bool) -> None:
        """Apply the Options switch. Logging starts off."""

        self.model.set_logging(enabled)
        self._logging.apply(self.model.logging_enabled)

    def revise_option(self, key: str, text: str) -> None:
        """Store one safety-limit field as typed. A preview reads it from the model."""

        self.model.set_option_text(key, text)

    def revise_limit(self, key: str, text: str) -> None:
        """Store one year or priority as typed."""

        self.model.set_limit_text(key, text)

    def sort_clusters(self, column: str) -> None:
        """Sort the cluster list by event number or file count, toggling direction."""

        if column not in {"number", "files"}:
            return
        chosen = self.model.toggle_sort(column)
        event("clusters_sorted", column=chosen[0], descending=chosen[1])

    def _dispatch_disk(self, wait: Wait, work, on_done) -> None:
        """Look up ``_run_disk`` on each call, so a test can replace that method."""

        self._run_disk(wait, work, on_done)

    def _run_disk(self, wait: Wait, work, on_done) -> None:
        """Run disk work through the injected runner, or through the window.

        ``on_done`` receives ``Success`` or ``Failure``. The session stays busy
        while ``work`` runs.
        """

        if self.model.busy:
            return
        self.model.set_busy(True)

        def finish(raw: object) -> None:
            self.model.set_busy(False)
            if isinstance(raw, BaseException):
                on_done(Failure(raw))
            else:
                on_done(Success(raw))

        (self._disk or self.ui.run_work)(wait, work, finish)

    def pattern_committed(self, iid: str, column: str, value: str) -> None:
        self._edits.pattern_committed(iid, column, value)

    def validate_pattern(self, description: str, source: str) -> None:
        self._edits.validate_pattern(description, source)

    def validate_row(self, iid: str) -> None:
        self._edits.validate_row(iid)

    def cell_text(self, iid: str, column: str) -> str:
        return self._edits.cell_text(iid, column)

    def add_pattern_rule(self) -> None:
        self._edits.add_pattern_rule()

    def remove_pattern_rule(self, iids: list[str]) -> None:
        self._edits.remove_pattern_rule(iids)

    def apply_clustering(self) -> None:
        self._relocation.apply()

    def flatten_clustering(self) -> None:
        self._relocation.flatten()

    def day_file_opened(self, row: int) -> None:
        self._opening.day_file_opened(row)

    def cluster_opened(self, index: int) -> None:
        self._opening.cluster_opened(index)

    def open_day_file(self, row: int) -> None:
        self._opening.open_day_file(row)

    def open_cluster_folder(self, index: int) -> None:
        self._opening.open_cluster_folder(index)


trace_module(sys.modules[__name__])
