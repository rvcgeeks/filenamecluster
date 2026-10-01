"""Semantic requests the controller sends. The view chooses the catalog words.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Generic, TypeVar

from filenamecluster.log import trace_module

T = TypeVar("T")


class Wait(Enum):
    """Why the window is waiting on disk work."""

    OPEN = auto()
    PREVIEW = auto()
    APPLY_CHECK = auto()
    APPLY = auto()
    NAME_CHECK = auto()
    FLATTEN_CHECK = auto()
    FLATTEN = auto()
    AFTER_FLATTEN = auto()
    AFTER_ERROR = auto()


@dataclass(frozen=True, slots=True)
class Success(Generic[T]):
    """A finished disk job and the value it returned."""

    value: T


@dataclass(frozen=True, slots=True)
class Failure:
    """A finished disk job that stopped on an exception."""

    error: BaseException


@dataclass(frozen=True, slots=True)
class PatternBlank:
    pass


@dataclass(frozen=True, slots=True)
class PatternValid:
    description: str


@dataclass(frozen=True, slots=True)
class PatternInvalid:
    detail: str


@dataclass(frozen=True, slots=True)
class NothingToMove:
    pass


@dataclass(frozen=True, slots=True)
class Applied:
    files: int
    events: int
    skipped: int = 0


@dataclass(frozen=True, slots=True)
class CouldNotMove:
    detail: str


@dataclass(frozen=True, slots=True)
class NothingToFlatten:
    pass


@dataclass(frozen=True, slots=True)
class Flattened:
    moved: int
    name: str


@dataclass(frozen=True, slots=True)
class CouldNotFlatten:
    detail: str


@dataclass(frozen=True, slots=True)
class FileMissing:
    name: str


@dataclass(frozen=True, slots=True)
class FolderMissing:
    name: str


@dataclass(frozen=True, slots=True)
class ApplyCreate:
    path: Path
    files: int
    events: int


@dataclass(frozen=True, slots=True)
class ApplyUpdate:
    path: Path
    files: int
    events: int


@dataclass(frozen=True, slots=True)
class FlattenAsk:
    folders: int
    path: Path
    noted: int = 0


Notice = (
    PatternBlank
    | PatternValid
    | PatternInvalid
    | NothingToMove
    | Applied
    | CouldNotMove
    | NothingToFlatten
    | Flattened
    | CouldNotFlatten
    | FileMissing
    | FolderMissing
)

Question = ApplyCreate | ApplyUpdate | FlattenAsk


trace_module(sys.modules[__name__])
