"""Keep a note on an event folder when Apply updates its stamp.

The note is the words a person added before or after the dates. Apply copies
that note onto the new stamp. This module does not ask and does not draw.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import sys
from pathlib import Path

from filenamecluster.core.parser.folders import (
    event_folder_parts,
    folder_note,
    is_cluster_folder_name,
    name_with_note,
)
from filenamecluster.log import trace_module


def noted_name(directory: Path | str, cluster) -> str:
    """The folder name Apply should use, with the dominant note kept."""

    note = _dominant_note(Path(directory), cluster)
    if note is None:
        return cluster.name
    return name_with_note(note[0], cluster.name, note[1])


def find_event_folder(directory: Path | str, cluster) -> Path | None:
    """The event folder for ``cluster``, including one whose name has a note."""

    root = Path(directory)
    exact = root / cluster.name
    if exact.is_dir():
        return exact
    parent = _dominant_parent(root, cluster)
    if parent is not None:
        return root / parent
    if not root.is_dir():
        return None
    for entry in sorted(root.iterdir(), key=lambda item: item.name):
        if not entry.is_dir():
            continue
        parts = event_folder_parts(entry.name)
        if parts is not None and parts[1] == cluster.name:
            return entry
    return None


def _dominant_note(directory: Path, cluster) -> tuple[str, str] | None:
    """The note on the event folder that already holds the most of these files."""

    counts: dict[tuple[str, str], int] = {}
    order: list[tuple[str, str]] = []
    for item in cluster.files:
        parent = _placed_parent(item)
        if parent is None or not (directory / parent).is_dir():
            continue
        note = folder_note(parent)
        if note is None:
            continue
        if note not in counts:
            order.append(note)
            counts[note] = 0
        counts[note] += 1
    best: tuple[str, str] | None = None
    for note in order:
        if best is None or counts[note] > counts[best]:
            best = note
    return best


def _dominant_parent(directory: Path, cluster) -> str | None:
    """The existing event folder that holds the most of these files."""

    counts: dict[str, int] = {}
    order: list[str] = []
    for item in cluster.files:
        parent = _placed_parent(item)
        if parent is None or not (directory / parent).is_dir():
            continue
        if parent not in counts:
            order.append(parent)
            counts[parent] = 0
        counts[parent] += 1
    best: str | None = None
    for name in order:
        if best is None or counts[name] > counts[best]:
            best = name
    return best


def _placed_parent(item) -> str | None:
    if not item.source:
        return None
    relative = Path(item.source)
    if len(relative.parts) != 2 or not is_cluster_folder_name(relative.parts[0]):
        return None
    return relative.parts[0]


trace_module(sys.modules[__name__])
