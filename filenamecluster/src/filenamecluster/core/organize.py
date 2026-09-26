"""Name events and move their files into one folder per event.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``. Introduction: ``readme.md``.

Cluster folders are named so a plain lexical sort follows time:

* same calendar day: ``1 12-08-2026 22.34.11 to 02.56.23``
* several days: ``1 12-08-2026 22.34.11 to 17-08-2026 02.56.23``

The number is the chronological position, starting at 1.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from filenamecluster.core.cluster import Cluster
from filenamecluster.core.parse import TimestampedFile, is_cluster_folder_name


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

    created: list[Path] = []
    kept: set[Path] = set()
    for cluster in clusters:
        folder = directory / cluster.name
        folder.mkdir(exist_ok=True)
        created.append(folder)
        kept.add(folder.resolve())
        for item in cluster.files:
            filename = _single_component(item.name)
            source = _source_path(directory, item, filename)
            if not source.is_file():
                raise FileNotFoundError(source)
            target = folder / filename
            if _same_file(source, target):
                continue
            if target.exists():
                raise FileExistsError(target)
            shutil.move(str(source), str(target))
    _remove_empty_event_folders(directory, kept)
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
                raise FileExistsError(target)
            moves.append((entry, target))
    for source, target in moves:
        shutil.move(source, target)
    for folder in folders:
        try:
            folder.rmdir()
        except OSError:
            continue
    return len(moves)


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
            continue
        try:
            entry.rmdir()
        except OSError:
            continue
