"""Open a Day detail file or an event folder with the operating system.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import sys

from filenamecluster.core import find_event_folder, locate_file
from filenamecluster.log import log_call, trace_module
from .ports import DialogPort
from .requests import FileMissing, FolderMissing


class OpenActions:
    """Resolve where a file or an event folder is now, then ask the system to open it."""

    def __init__(self, model, files, ui: DialogPort) -> None:
        self._model = model
        self._files = files
        self._ui = ui

    def day_file_opened(self, row: int) -> None:
        self.open_day_file(row)

    def cluster_opened(self, index: int) -> None:
        if index != self._model.selected_cluster:
            return
        self.open_cluster_folder(index)

    def open_day_file(self, row: int) -> None:
        """Open one Day detail row with the operating system's default app."""

        found = self._model.day_file(row)
        if self._model.directory is None or found is None:
            return
        item, index = found
        path = locate_file(self._model.directory, item, self._cluster_name(index))
        if path is None:
            self._ui.tell(FileMissing(item.name))
            return
        log_call("filenamecluster.ui.controller.files.open_file")
        self._files.open_file(path)

    def open_cluster_folder(self, index: int) -> None:
        """Open the event folder in its own file-manager window when it exists."""

        if self._model.directory is None or self._model.result is None:
            return
        if not 0 <= index < len(self._model.result.clusters):
            return
        cluster = self._model.result.clusters[index]
        folder = find_event_folder(self._model.directory, cluster)
        if folder is not None:
            log_call("filenamecluster.ui.controller.files.open_folder_window")
            self._files.open_folder_window(folder)
            return
        self._ui.tell(FolderMissing(cluster.name))

    def _cluster_name(self, index: int) -> str:
        result = self._model.result
        if result is None or not 0 <= index < len(result.clusters):
            return ""
        return result.clusters[index].name


trace_module(sys.modules[__name__])
