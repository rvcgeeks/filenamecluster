"""Rename one cluster folder without letting the stamp change.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import sys

from filenamecluster.core import event_folder_parts, find_event_folder, keep_folder_notes, name_with_note
from filenamecluster.log import trace_module
from .requests import RenameRejected

_FORBIDDEN = set('/\\:*?"<>|\n\r')


class FolderNotes:
    """Apply a prefix and suffix around the stamp the session already computed."""

    def __init__(self, model, ui) -> None:
        self.model = model
        self.ui = ui

    def stamp(self, index: int) -> str:
        result = self.model.result
        if result is None or not 0 <= index < len(result.clusters):
            return ""
        return result.clusters[index].name

    def note(self, index: int) -> tuple[str, str]:
        return self.model.folder_notes.get(self.stamp(index))

    def rename(self, index: int, prefix: str, suffix: str) -> None:
        result = self.model.result
        directory = self.model.directory
        if result is None or directory is None or not 0 <= index < len(result.clusters):
            return
        prefix, suffix = prefix.strip(), suffix.strip()
        if any(char in prefix + suffix for char in _FORBIDDEN):
            self.ui.tell(RenameRejected("invalid"))
            return
        stamp = result.clusters[index].name
        composed = name_with_note(prefix, stamp, suffix)
        parts = event_folder_parts(composed)
        if parts is None or parts[1] != stamp:
            self.ui.tell(RenameRejected("invalid"))
            return
        prefix, suffix = parts[0], parts[2]
        folder = find_event_folder(directory, result.clusters[index])
        if folder is not None and folder.name != composed:
            target = folder.with_name(composed)
            if target.exists():
                self.ui.tell(RenameRejected("exists", composed))
                return
            try:
                folder.rename(target)
            except OSError as exc:
                self.ui.tell(RenameRejected("failed", detail=str(exc)))
                return
        self.model.replace_folder_note(stamp, prefix, suffix)
        keep_folder_notes(directory, self.model.folder_notes.as_dict())


trace_module(sys.modules[__name__])
