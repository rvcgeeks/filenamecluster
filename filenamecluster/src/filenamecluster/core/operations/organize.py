"""Name events and move their files into one folder per event.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``. Introduction: ``readme.md``.

Cluster folders are named so a plain lexical sort follows time:

* same calendar day: ``1 12-08-2026 22.34.11 to 02.56.23``
* several days: ``1 12-08-2026 22.34.11 to 17-08-2026 02.56.23``

The number is the chronological position, starting at 1. Words placed
before or after that stamp are kept when Apply updates the folder.
"""

from __future__ import annotations

import sys
from filenamecluster.log import detail, trace_module

from collections.abc import Collection
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from filenamecluster.core.algorithm.cluster import Cluster
from filenamecluster.core.parser import TimestampedFile, is_cluster_folder_name


@dataclass(frozen=True, slots=True)
class NamedCluster:
    """A cluster plus the folder name it should use."""

    number: int
    name: str
    files: tuple[TimestampedFile, ...]

    @property
    def start(self) -> datetime:
        return self.files[0].timestamp

    @property
    def end(self) -> datetime:
        return self.files[-1].timestamp


def cluster_name(number: int, start: datetime, end: datetime) -> str:
    """Build the chronological folder name for one event."""

    if number < 1:
        raise ValueError("cluster number must start at 1")
    if start.date() == end.date():
        return f"{number} {start:%d-%m-%Y} {start:%H.%M.%S} to {end:%H.%M.%S}"
    return f"{number} {start:%d-%m-%Y %H.%M.%S} to {end:%d-%m-%Y %H.%M.%S}"


def name_clusters(clusters: list[Cluster] | tuple[Cluster, ...]) -> list[NamedCluster]:
    """Number clusters in their existing order, which is chronological."""

    return [
        NamedCluster(
            number=number,
            name=cluster_name(number, cluster.start, cluster.end),
            files=cluster.files,
        )
        for number, cluster in enumerate(clusters, start=1)
    ]


def plan_cluster_moves(
    root: Path | str,
    clusters: list[NamedCluster] | tuple[NamedCluster, ...],
    source: Path | str | None = None,
):
    """The moves Apply would make, including filenames the destination already has."""

    from filenamecluster.core.operations.placement import plan_cluster_moves as plan

    return plan(root, _keeping_notes(root, clusters, source), source)


def plan_flatten_moves(root: Path | str):
    """The moves Flatten would make, including filenames the folder already has."""

    from filenamecluster.core.operations.placement import plan_flatten_moves as plan

    return plan(root)


def move_into_cluster_folders(
    root: Path | str,
    clusters: list[NamedCluster] | tuple[NamedCluster, ...],
    replacing: Collection[Path] | None = None,
    source: Path | str | None = None,
) -> list[Path]:
    """Create one folder per cluster under ``root`` and move its files in.

    Names must be a single path component. When ``replacing`` is omitted, a
    destination that already has the filename is left untouched and reported
    as ``FileExistsError`` before anything is moved. When ``replacing`` is
    given, those source paths overwrite the destination and every other
    clash is left where it is.
    """

    from filenamecluster.core.operations.placement import (
        commit_cluster_moves,
        plan_cluster_moves as plan,
    )

    clusters = _keeping_notes(root, clusters, source)
    if replacing is None:
        planned = plan(root, clusters, source)
        if planned.clashes:
            clash = planned.clashes[0]
            detail("move_blocked", source=str(clash.source), target=str(clash.target))
            raise FileExistsError(clash.target)
        replacing = ()
    return commit_cluster_moves(root, clusters, replacing, source)


def flatten_cluster_folders(
    root: Path | str,
    replacing: Collection[Path] | None = None,
    plan=None,
) -> int:
    """Move files out of event folders back into ``root`` and remove those folders.

    Only immediate subfolders whose names match an event folder are touched.
    Other folders stay. When ``replacing`` is omitted, a name that already
    exists in ``root`` is reported as ``FileExistsError`` and nothing is
    moved. When ``replacing`` is given, those source paths overwrite and
    every other clash stays in its event folder. Returns how many files moved.
    """

    from filenamecluster.core.operations.placement import commit_flatten_moves

    if replacing is None:
        planned = plan_flatten_moves(root) if plan is None else plan
        if planned.clashes:
            clash = planned.clashes[0]
            detail("flatten_blocked", source=str(clash.source), target=str(clash.target))
            raise FileExistsError(clash.target)
        replacing = ()
    return commit_flatten_moves(root, replacing, plan)


def is_folder(path: Path | str) -> bool:
    """Whether ``path`` is a directory."""

    return Path(path).is_dir()


def event_folder_names(directory: Path | str) -> list[str]:
    """Names of event folders directly inside ``directory``."""

    return [
        entry.name
        for entry in Path(directory).iterdir()
        if entry.is_dir() and is_cluster_folder_name(entry.name)
    ]


def folder_note(name: str) -> tuple[str, str] | None:
    """Words before and after an event-folder stamp, or ``None`` when absent."""

    from filenamecluster.core.parser.folders import folder_note as note

    return note(name)


def find_event_folder(directory: Path | str, cluster: NamedCluster) -> Path | None:
    """The event folder for ``cluster``, including one renamed with a note."""

    from filenamecluster.core.operations.notes import find_event_folder as find

    return find(directory, cluster)


def event_folder(directory: Path | str, name: str) -> Path | None:
    """The event folder when it exists on disk."""

    folder = Path(directory) / name
    if folder.is_dir():
        return folder
    return None


def locate_file(
    directory: Path | str,
    item: TimestampedFile,
    cluster_name: str,
    source: Path | str | None = None,
) -> Path | None:
    """Where ``item`` sits now, including an event folder created by Apply."""

    root = Path(directory)
    try:
        current = _source_path(root, item, item.name, source)
    except ValueError:
        return None
    if current.is_file():
        return current
    if not cluster_name:
        return None
    try:
        placed = _source_path(
            root,
            TimestampedFile(item.name, item.timestamp, source=f"{cluster_name}/{item.name}"),
            item.name,
        )
    except ValueError:
        return None
    if placed.is_file():
        return placed
    return None


def _keeping_notes(
    root: Path | str,
    clusters: list[NamedCluster] | tuple[NamedCluster, ...],
    source: Path | str | None = None,
):
    """Copy each cluster, using a folder name that still carries its note."""

    from filenamecluster.core.operations.model import load_folder_notes
    from filenamecluster.core.operations.notes import noted_name

    directory = Path(root)
    saved = load_folder_notes(directory)
    renamed: list[NamedCluster] = []
    for cluster in clusters:
        name = noted_name(directory, cluster, saved, source)
        if name == cluster.name:
            renamed.append(cluster)
            continue
        renamed.append(NamedCluster(number=cluster.number, name=name, files=cluster.files))
    return renamed


def _single_component(name: str) -> str:
    if not name or name != Path(name).name or name in {".", ".."}:
        raise ValueError(f"unsafe filename: {name}")
    return name


def _source_path(
    directory: Path,
    item: TimestampedFile,
    filename: str,
    source: Path | str | None = None,
) -> Path:
    """Where ``item`` sits now: storage, the input folder, or an event folder."""

    root = directory
    if getattr(item, "origin", "") == "input" and source is not None:
        root = Path(source)
    relative = Path(item.source) if item.source else Path(filename)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise ValueError(f"unsafe filename: {item.source or filename}")
    if len(relative.parts) == 1:
        if relative.name != filename:
            raise ValueError(f"unsafe filename: {item.source}")
    elif len(relative.parts) == 2 and is_cluster_folder_name(relative.parts[0]):
        if relative.parts[1] != filename:
            raise ValueError(f"unsafe filename: {item.source}")
    else:
        raise ValueError(f"unsafe filename: {item.source or filename}")
    return root / relative


def _same_file(source: Path, target: Path) -> bool:
    if not source.exists() or not target.exists():
        return False
    return source.resolve() == target.resolve()


def _remove_empty_event_folders(directory: Path, kept: set[Path]) -> None:
    """Drop event folders this apply left empty, including ones just created."""

    for entry in directory.iterdir():
        if not entry.is_dir() or not is_cluster_folder_name(entry.name):
            continue
        try:
            entry.rmdir()
            detail("event_folder_removed", name=entry.name)
        except OSError:
            reason = "still_used" if entry.resolve() in kept else "not_empty"
            detail("event_folder_kept", name=entry.name, reason=reason)
            continue

trace_module(sys.modules[__name__])
