"""Plan a move, then carry it out once each name clash has a decision.

The window asks before a destination filename is overwritten. This module
does not ask. It reports the clashes and, given the sources that may
overwrite, moves or leaves each file.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import os
import shutil
import sys
from collections.abc import Collection
from dataclasses import dataclass
from pathlib import Path

from filenamecluster.log import detail, trace_module


@dataclass(frozen=True, slots=True)
class PlannedMove:
    """One file and the path it would take."""

    source: Path
    target: Path


@dataclass(frozen=True, slots=True)
class PlacementPlan:
    """Moves whose names are free, and moves whose names are already taken."""

    moves: tuple[PlannedMove, ...]
    clashes: tuple[PlannedMove, ...]


def plan_cluster_moves(root: Path | str, clusters) -> PlacementPlan:
    """The moves Apply would make. Nothing is created or moved."""

    filing = _filing()
    directory = _directory(root)
    moves: list[PlannedMove] = []
    clashes: list[PlannedMove] = []
    claimed: set[Path] = set()
    for cluster in clusters:
        folder = directory / cluster.name
        for item in cluster.files:
            filename = filing._single_component(item.name)
            source = filing._source_path(directory, item, filename)
            if not source.is_file():
                detail("move_missing", source=str(source))
                raise FileNotFoundError(source)
            _classify(source, folder / filename, moves, clashes, claimed)
    detail("move_planned", files=len(moves), clashes=len(clashes))
    return PlacementPlan(tuple(moves), tuple(clashes))


def plan_flatten_moves(root: Path | str) -> PlacementPlan:
    """The moves Flatten would make. Nothing is moved."""

    filing = _filing()
    directory = _directory(root)
    folders = [
        entry
        for entry in directory.iterdir()
        if entry.is_dir() and filing.is_cluster_folder_name(entry.name)
    ]
    moves: list[PlannedMove] = []
    clashes: list[PlannedMove] = []
    claimed: set[Path] = set()
    for folder in folders:
        for entry in folder.iterdir():
            if not entry.is_file():
                continue
            target = directory / filing._single_component(entry.name)
            _classify(entry, target, moves, clashes, claimed)
    detail("flatten_planned", files=len(moves), clashes=len(clashes), folders=len(folders))
    return PlacementPlan(tuple(moves), tuple(clashes))


def commit_cluster_moves(
    root: Path | str,
    clusters,
    replacing: Collection[Path],
) -> list[Path]:
    """Create the event folders and move. Sources in ``replacing`` overwrite."""

    filing = _filing()
    directory = _directory(root)
    detail("move_started", path=str(directory), events=len(clusters))
    allowed = _resolved(replacing)
    created: list[Path] = []
    kept: set[Path] = set()
    claimed: set[Path] = set()
    for cluster in clusters:
        folder = directory / cluster.name
        folder.mkdir(exist_ok=True)
        detail("event_folder_ready", name=cluster.name, files=len(cluster.files))
        created.append(folder)
        kept.add(folder.resolve())
        for item in cluster.files:
            filename = filing._single_component(item.name)
            source = filing._source_path(directory, item, filename)
            if not source.is_file():
                detail("move_missing", source=str(source))
                raise FileNotFoundError(source)
            _place(source, folder / filename, allowed, claimed)
    filing._remove_empty_event_folders(directory, kept)
    detail("move_finished", folders=len(created))
    return created


def commit_flatten_moves(root: Path | str, replacing: Collection[Path]) -> int:
    """Move event-folder files back. Sources in ``replacing`` overwrite."""

    filing = _filing()
    directory = _directory(root)
    detail("flatten_started", path=str(directory))
    plan = plan_flatten_moves(directory)
    allowed = _resolved(replacing)
    claimed: set[Path] = set()
    moved = 0
    for item in (*plan.moves, *plan.clashes):
        if _place(item.source, item.target, allowed, claimed):
            moved += 1
    folders = [
        entry
        for entry in directory.iterdir()
        if entry.is_dir() and filing.is_cluster_folder_name(entry.name)
    ]
    for folder in folders:
        try:
            folder.rmdir()
            detail("event_folder_removed", name=folder.name)
        except OSError:
            detail("event_folder_kept", name=folder.name)
            continue
    detail("flatten_finished", moved=moved)
    return moved


def _directory(root: Path | str) -> Path:
    directory = Path(root)
    if not directory.is_dir():
        raise NotADirectoryError(directory)
    return directory


def _classify(source: Path, target: Path, moves: list[PlannedMove], clashes: list[PlannedMove], claimed: set[Path]) -> None:
    filing = _filing()
    if filing._same_file(source, target):
        detail("file_already_placed", path=str(target))
        return
    if target.exists() or target in claimed:
        detail("move_blocked", source=str(source), target=str(target))
        clashes.append(PlannedMove(source, target))
        return
    moves.append(PlannedMove(source, target))
    claimed.add(target)


def _place(source: Path, target: Path, allowed: set[Path], claimed: set[Path]) -> bool:
    """Move ``source`` to ``target``. Return whether a file changed place."""

    filing = _filing()
    if filing._same_file(source, target):
        detail("file_already_placed", path=str(target))
        return False
    taken = target.exists() or target in claimed
    if taken and source.resolve() not in allowed:
        detail("file_skipped", source=str(source), target=str(target))
        return False
    if taken:
        _overwrite(source, target)
        detail("file_replaced", source=str(source), target=str(target))
    else:
        shutil.move(str(source), str(target))
        detail("file_moved", source=str(source), target=str(target))
    claimed.add(target)
    return True


def _overwrite(source: Path, target: Path) -> None:
    try:
        os.replace(source, target)
    except OSError:
        if target.is_file():
            target.unlink()
        shutil.move(str(source), str(target))


def _resolved(paths: Collection[Path]) -> set[Path]:
    return {Path(path).resolve() for path in paths}


def _filing():
    from filenamecluster.core.operations import organize

    return organize


trace_module(sys.modules[__name__])
