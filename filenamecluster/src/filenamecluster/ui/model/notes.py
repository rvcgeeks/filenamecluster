"""Words around an event-folder stamp, for the cluster list only.

The stamp itself stays the name calculations use. A folder on disk wins
over a note saved in the model file. An empty note is a cleared name.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import sys
from pathlib import Path

from filenamecluster.core.operations import load_folder_notes
from filenamecluster.core.parser.folders import event_folder_parts, is_cluster_folder_name, name_with_note
from filenamecluster.log import trace_module
from .display import ShownEvent


class FolderNoteBook:
    """Notes for the open folder. The cluster list reads this. The stamp does not."""

    def __init__(self) -> None:
        self._notes: dict[str, tuple[str, str]] = {}

    def seed(self, directory, result) -> None:
        self._notes = seed_folder_notes(directory, result)

    def get(self, stamp: str) -> tuple[str, str]:
        return self._notes.get(stamp, ("", ""))

    def as_dict(self) -> dict[str, tuple[str, str]]:
        return dict(self._notes)

    def replace(self, stamp: str, prefix: str, suffix: str) -> None:
        if prefix or suffix:
            self._notes[stamp] = (prefix, suffix)
        else:
            self._notes.pop(stamp, None)


def seed_folder_notes(directory, result) -> dict[str, tuple[str, str]]:
    """Notes for the current events. Disk wins, then the model file.

    The chosen folder is listed once. Each event then reads that list.
    """

    if directory is None or result is None:
        return {}
    saved = load_folder_notes(directory)
    root = Path(directory)
    names, by_stamp = _event_folders(root)
    notes: dict[str, tuple[str, str]] = {}
    for cluster in result.clusters:
        disk = _disk_note(cluster, names, by_stamp)
        if disk is not None:
            if disk[0] or disk[1]:
                notes[cluster.name] = disk
            continue
        saved_note = saved.get(cluster.name)
        if saved_note:
            notes[cluster.name] = saved_note
    return notes


def _event_folders(root: Path) -> tuple[set[str], dict[str, tuple[str, str]]]:
    """Directory names, and the first event folder for each stamp."""

    names: set[str] = set()
    by_stamp: dict[str, tuple[str, str]] = {}
    if not root.is_dir():
        return names, by_stamp
    try:
        found = [entry.name for entry in root.iterdir() if entry.is_dir()]
    except OSError:
        return names, by_stamp
    names.update(found)
    for name in sorted(found):
        parts = event_folder_parts(name)
        if parts is None:
            continue
        prefix, stamp, suffix = parts
        by_stamp.setdefault(stamp, (prefix, suffix))
    return names, by_stamp


def _disk_note(cluster, names: set[str], by_stamp: dict[str, tuple[str, str]]):
    """Words on the existing folder, or ``None`` when that folder is absent.

    ``("", "")`` means the folder is there and has no extra words.
    """

    if cluster.name in names:
        return ("", "")
    parent = _dominant_parent(cluster, names)
    if parent is not None:
        parts = event_folder_parts(parent)
        if parts is not None and parts[1] == cluster.name:
            return (parts[0], parts[2])
        return None
    return by_stamp.get(cluster.name)


def _dominant_parent(cluster, names: set[str]) -> str | None:
    """The event folder that already holds the most of this event's files."""

    counts: dict[str, int] = {}
    order: list[str] = []
    for item in cluster.files:
        source = item.source
        if not source:
            continue
        parts = Path(source).parts
        if len(parts) != 2 or parts[0] not in names or not is_cluster_folder_name(parts[0]):
            continue
        parent = parts[0]
        if parent not in counts:
            order.append(parent)
            counts[parent] = 0
        counts[parent] += 1
    best: str | None = None
    for name in order:
        if best is None or counts[name] > counts[best]:
            best = name
    return best


def noted_events(events, notes: dict[str, tuple[str, str]]):
    """Draw names with the note around the stamp. Times stay on the event."""

    if not notes:
        return events
    titled = []
    for event in events:
        prefix, suffix = notes.get(event.name, ("", ""))
        name = name_with_note(prefix, event.name, suffix) if prefix or suffix else event.name
        titled.append(ShownEvent(event.number, name, event.start, event.end, event.files))
    return tuple(titled)


trace_module(sys.modules[__name__])
