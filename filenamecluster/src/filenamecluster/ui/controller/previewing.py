"""Load a folder and preview it again.

Core scans the disk. This class records the preview and the status line.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import sys
from pathlib import Path

from filenamecluster.core import (
    CurrentPreview,
    FolderPreview,
    FolderScan,
    ModelOptions,
    OptionError,
    OptionReader,
    SavedOptionsState,
    ScanState,
)
from filenamecluster.log import event, trace_module
from .ports import DiskPort
from .requests import Failure, Success, Wait


class FolderPreviewing:
    """Turn a chosen folder into a session preview. Dialogs stay with the caller."""

    def __init__(self, model, disk: DiskPort) -> None:
        self.model = model
        self.disk = disk
        self._preview = FolderPreview()
        self._reader = OptionReader()

    def load_folder(self, folder: Path) -> None:
        if self.model.busy:
            return
        self.model.set_directory(Path(folder))
        event("folder_chosen", path=str(self.model.directory))
        directory = self.model.directory
        self.disk(Wait.OPEN, lambda: self._preview.scan(directory), self._finish_folder_load)

    def refresh(self, on_ready=None, wait: Wait = Wait.PREVIEW) -> None:
        """Re-scan the folder. ``on_ready`` receives True when a preview is stored."""

        def report(ok: bool) -> None:
            if on_ready is not None:
                on_ready(ok)

        if self.model.busy:
            return
        if self.model.directory is None:
            self.model.show_choose()
            report(False)
            return
        table = self.model.pattern_table()
        try:
            prepared = self._preview.prepare(
                self.model.option_drafts(), self.model.limit_drafts(), table
            )
        except OptionError as exc:
            self.model.show_option_problem(exc)
            event("preview_rejected", path=str(self.model.directory))
            report(False)
            return
        except ValueError as exc:
            self.model.show_value_problem(str(exc))
            event("preview_rejected", path=str(self.model.directory))
            report(False)
            return
        directory = self.model.directory

        def work():
            return self._preview.current(directory, prepared)

        def on_done(outcome: Success[CurrentPreview] | Failure) -> None:
            if isinstance(outcome, Failure):
                error = outcome.error
                if isinstance(error, OSError):
                    self.model.show_read_failure(directory, error)
                    event("preview_failed", path=str(directory))
                    report(False)
                    return
                raise error
            preview = outcome.value
            self._store_preview(preview.result, len(preview.invalid))
            event(
                "preview_ready",
                path=str(directory),
                events=len(preview.result.clusters),
                files=preview.result.file_count,
            )
            report(True)

        self.disk(wait, work, on_done)

    def _finish_folder_load(self, outcome: Success[FolderScan] | Failure) -> None:
        """Store a folder scan on the session."""

        if isinstance(outcome, Failure):
            raise outcome.error
        scan = outcome.value
        directory = self.model.directory
        options = scan.options
        loaded = scan.saved is SavedOptionsState.LOADED and isinstance(options, ModelOptions)
        if loaded and self._reader.accepts(options):
            self.model.apply_saved(options)
            event("options_loaded", path=str(directory))
        else:
            if loaded or scan.saved is SavedOptionsState.IGNORED:
                event("options_ignored", path=str(directory))
            self.model.reset_builtin()
        if scan.state is ScanState.READ_ERROR:
            self.model.show_read_failure(directory, scan.error or OSError("unreadable folder"))
            event("preview_failed", path=str(directory))
            return
        invalid = sum(1 for row in self.model.pattern_rows() if row.invalid)
        result = scan.result
        if result is None:
            raise TypeError("folder scan had no result")
        self._store_preview(result, invalid)
        event(
            "preview_ready",
            path=str(directory),
            events=len(result.clusters),
            files=result.file_count,
        )

    def _store_preview(self, result, invalid: int) -> None:
        self.model.remember_preview(result, invalid)


trace_module(sys.modules[__name__])
