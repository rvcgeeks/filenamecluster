"""Apply and Flatten: confirm, resolve name clashes, then move the files.

Core moves the files. This class asks the window and records the result.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

from filenamecluster.core import (
    flatten_cluster_folders,
    folder_note,
    is_cluster_folder_name,
    is_folder,
    move_into_cluster_folders,
    plan_cluster_moves,
    survey_flatten,
)
from filenamecluster.log import event, log_call, trace_module
from filenamecluster.ui.model import PreviewStaysStatus
from .clashes import ClashResolver
from .ports import DialogPort, DiskPort
from .requests import (
    Applied,
    ApplyCreate,
    ApplyUpdate,
    CouldNotFlatten,
    CouldNotMove,
    Failure,
    FlattenAsk,
    Flattened,
    NothingToFlatten,
    NothingToMove,
    Success,
    Transfer,
    Wait,
)


class FolderRelocation:
    """Ask before files move, move them through core, and record what happened."""

    def __init__(self, model, ui: DialogPort, disk: DiskPort, refresh) -> None:
        self.model = model
        self.ui = ui
        self.disk = disk
        self.refresh = refresh
        self._clashes = ClashResolver(ui)

    def apply(self) -> None:
        if self.model.busy or self.model.directory is None:
            return
        self.refresh(on_ready=self._confirm_apply, wait=Wait.APPLY_CHECK, reuse=True)

    def flatten(self) -> None:
        if self.model.busy:
            return
        directory = self.model.directory
        if directory is None or not is_folder(directory):
            return

        def list_folders():
            return survey_flatten(directory)

        def after_list(outcome: Success | Failure) -> None:
            if isinstance(outcome, Failure):
                error = outcome.error
                if isinstance(error, OSError):
                    self.ui.tell(CouldNotFlatten(str(error)))
                    return
                raise error
            names, plan = outcome.value
            self._confirm_flatten(directory, names, plan)

        self.disk(Wait.FLATTEN_CHECK, list_folders, after_list)

    def _confirm_apply(self, ready: bool) -> None:
        """Ask, after the preview, whether to move the files."""

        if not ready or self.model.result is None or self.model.directory is None:
            return
        result = self.model.result
        if not result.clusters:
            self.ui.tell(NothingToMove())
            return
        directory = self.model.directory
        source = self.model.input_directory
        already_clustered = any(
            is_cluster_folder_name(name) for name in result.ignored_directories
        )
        question = (
            ApplyUpdate(directory, result.file_count, len(result.clusters), source)
            if already_clustered
            else ApplyCreate(directory, result.file_count, len(result.clusters), source)
        )
        if source is None:
            if not self.ui.ask(question):
                event("apply_cancelled", path=str(directory))
                return
            copying = False
        else:
            choice = self.ui.ask_transfer(question)
            if choice is None:
                event("apply_cancelled", path=str(directory))
                return
            copying = choice is Transfer.COPY
        discard = source is None
        clusters = result.clusters
        files, events = result.file_count, len(result.clusters)

        def finish(outcome: Success | Failure, skipped: int) -> None:
            if isinstance(outcome, Failure):
                self._failed(outcome, directory, CouldNotMove, "apply_failed")
                return
            kept = files - skipped
            if skipped and discard:
                self.ui.tell(Applied(kept, events, deleted=skipped))
                event("apply_finished", path=str(directory), files=kept, events=events, deleted=skipped)
                self.refresh(wait=Wait.PREVIEW)
                return
            if skipped:
                self.ui.tell(Applied(kept, events, skipped=skipped))
                event("apply_finished", path=str(directory), files=kept, events=events, skipped=skipped)
                self.refresh(wait=Wait.PREVIEW)
                return
            self.ui.tell(Applied(files, events))
            self.model.set_actions_and_status(
                False,
                True,
                PreviewStaysStatus(files=files, events=events),
            )
            event("apply_finished", path=str(directory), files=files, events=events)

        def after_plan(outcome: Success | Failure) -> None:
            if isinstance(outcome, Failure):
                self._failed(outcome, directory, CouldNotMove, "apply_failed")
                return
            self._commit(
                directory,
                outcome.value.clashes,
                Wait.APPLY,
                lambda replacing: move_into_cluster_folders(
                    directory,
                    clusters,
                    replacing=replacing,
                    source=source,
                    copying=copying,
                    delete_skipped=discard,
                ),
                finish,
                "apply_cancelled",
                "filenamecluster.core.move_into_cluster_folders",
                discard=discard,
            )

        log_call("filenamecluster.core.plan_cluster_moves")
        self.disk(Wait.NAME_CHECK, lambda: plan_cluster_moves(directory, clusters, source), after_plan)

    def _confirm_flatten(self, directory: Path, folders, plan) -> None:
        """Ask, after the folder list, whether to move the files back."""

        if not folders:
            self.ui.tell(NothingToFlatten())
            return
        noted = sum(1 for name in folders if folder_note(name))
        if not self.ui.ask(FlattenAsk(len(folders), directory, noted=noted)):
            event("flatten_cancelled", path=str(directory))
            return

        def finish(outcome: Success | Failure, _skipped: int) -> None:
            if isinstance(outcome, Failure):
                self._failed(outcome, directory, CouldNotFlatten, "flatten_failed")
                return
            moved = outcome.value
            self.ui.tell(Flattened(moved, directory.name))
            event("flatten_finished", path=str(directory), moved=moved)
            self.refresh(wait=Wait.AFTER_FLATTEN)

        discard = self.model.input_directory is None
        self._commit(
            directory,
            plan.clashes,
            Wait.FLATTEN,
            lambda replacing: flatten_cluster_folders(
                directory, replacing=replacing, plan=plan, delete_skipped=discard
            ),
            finish,
            "flatten_cancelled",
            "filenamecluster.core.flatten_cluster_folders",
            discard=discard,
        )

    def _commit(
        self,
        directory,
        clashes,
        wait,
        commit,
        finish,
        cancel_name: str,
        call_name: str,
        *,
        discard: bool = False,
    ) -> None:
        """Ask about each clash, then move on the disk thread."""

        replacing = self._clashes.replacing(clashes, discard=discard)
        if replacing is None:
            event(cancel_name, path=str(directory))
            return
        keys = {path.resolve() for path in replacing}
        skipped = sum(1 for clash in clashes if clash.source.resolve() not in keys)

        def wrapped(outcome: Success | Failure) -> None:
            finish(outcome, skipped)

        log_call(call_name)
        self.disk(wait, lambda: commit(replacing), wrapped)

    def _failed(self, outcome: Failure, directory: Path, notice: Callable, name: str) -> None:
        error = outcome.error
        if isinstance(error, (OSError, ValueError)):
            self.ui.tell(notice(str(error)))
            event(name, path=str(directory))
            self.refresh(wait=Wait.AFTER_ERROR)
            return
        raise error


trace_module(sys.modules[__name__])
