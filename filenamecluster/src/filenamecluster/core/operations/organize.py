"""Name events and move their files into one folder per event.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``. Introduction: ``readme.md``.

Cluster folders are named so a plain lexical sort follows time:

* same calendar day: ``1 12-08-2026 22.34.11 to 02.56.23``
* several days: ``1 12-08-2026 22.34.11 to 17-08-2026 02.56.23``

The number is the chronological position, starting at 1.
"""

from __future__ import annotations

import sys
from filenamecluster.log import detail, trace_module

import shutil
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


def move_into_cluster_folders(
    root: Path | str,
    clusters: list[NamedCluster] | tuple[NamedCluster, ...],
) -> list[Path]:
    """Create one folder per cluster under ``root`` and move its files in.

    Names must be a single path component. Existing destination files are
    left untouched and reported as ``FileExistsError``.
    """

    directory = Path(root)
    if not directory.is_dir():
        raise NotADirectoryError(directory)
    detail("move_started", path=str(directory), events=len(clusters))

    created: list[Path] = []
    kept: set[Path] = set()
    for cluster in clusters:
        folder = directory / cluster.name
        folder.mkdir(exist_ok=True)
        detail("event_folder_ready", name=cluster.name, files=len(cluster.files))
        created.append(folder)
        kept.add(folder.resolve())
        for item in cluster.files:
            filename = _single_component(item.name)
            source = _source_path(directory, item, filename)
            if not source.is_file():
                detail("move_missing", source=str(source))
                raise FileNotFoundError(source)
            target = folder / filename
            if _same_file(source, target):
                detail("file_already_placed", path=str(target))
                continue
            if target.exists():
                detail("move_blocked", source=str(source), target=str(target))
                raise FileExistsError(target)
            shutil.move(str(source), str(target))
            detail("file_moved", source=str(source), target=str(target))
    _remove_empty_event_folders(directory, kept)
    detail("move_finished", folders=len(created))
    return created


def flatten_cluster_folders(root: Path | str) -> int:
    """Move files out of event folders back into ``root`` and remove those folders.

    Only immediate subfolders whose names match an event folder are touched.
    Other folders stay. A name that already exists in ``root`` is reported as
    ``FileExistsError`` and nothing is moved. Returns how many files moved.
    """

    directory = Path(root)
    if not directory.is_dir():
        raise NotADirectoryError(directory)
    detail("flatten_started", path=str(directory))

    folders = [
        entry
        for entry in directory.iterdir()
        if entry.is_dir() and is_cluster_folder_name(entry.name)
    ]
    moves: list[tuple[Path, Path]] = []
    for folder in folders:
        for entry in folder.iterdir():
            if not entry.is_file():
                continue
            target = directory / _single_component(entry.name)
            if target.exists():
                detail("flatten_blocked", source=str(entry), target=str(target))
                raise FileExistsError(target)
            moves.append((entry, target))
    detail("flatten_planned", files=len(moves), folders=len(folders))
    for source, target in moves:
        shutil.move(source, target)
        detail("file_moved", source=str(source), target=str(target))
    for folder in folders:
        try:
            folder.rmdir()
            detail("event_folder_removed", name=folder.name)
        except OSError:
            detail("event_folder_kept", name=folder.name)
            continue
    detail("flatten_finished", moved=len(moves))
    return len(moves)


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


def event_folder(directory: Path | str, name: str) -> Path | None:
    """The event folder when it exists on disk."""

    folder = Path(directory) / name
    if folder.is_dir():
        return folder
    return None


def locate_file(directory: Path | str, item: TimestampedFile, cluster_name: str) -> Path | None:
    """Where ``item`` sits now, including an event folder created by Apply."""

    root = Path(directory)
    try:
        current = _source_path(root, item, item.name)
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


def _single_component(name: str) -> str:
    if not name or name != Path(name).name or name in {".", ".."}:
        raise ValueError(f"unsafe filename: {name}")
    return name


def _source_path(directory: Path, item: TimestampedFile, filename: str) -> Path:
    """Where ``item`` sits now: the chosen folder, or one event folder inside it."""

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
    return directory / relative


def _same_file(source: Path, target: Path) -> bool:
    if not source.exists() or not target.exists():
        return False
    return source.resolve() == target.resolve()


def _remove_empty_event_folders(directory: Path, kept: set[Path]) -> None:
    """Drop event folders that this apply emptied and no longer uses."""

    for entry in directory.iterdir():
        if not entry.is_dir() or not is_cluster_folder_name(entry.name):
            continue
        if entry.resolve() in kept:
            detail("event_folder_kept", name=entry.name, reason="still_used")
            continue
        try:
            entry.rmdir()
            detail("event_folder_removed", name=entry.name)
        except OSError:
            detail("event_folder_kept", name=entry.name, reason="not_empty")
            continue

trace_module(sys.modules[__name__])
