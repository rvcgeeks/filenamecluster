"""Plain values the window can draw. No widgets.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import Enum, auto
from pathlib import Path

from filenamecluster.core import OptionFault, OptionField
from filenamecluster.log import trace_module


class SkippedReason(Enum):
    """Why one path did not become a file in the preview."""

    EVENT_FOLDER = auto()
    SUBFOLDER = auto()
    NO_TIMESTAMP = auto()


class LearnedKind(Enum):
    """The learned boundary facts the view can describe."""

    NONE = auto()
    ONE_GROUP = auto()
    BOUNDARY = auto()


@dataclass(frozen=True, slots=True)
class LearnedSummary:
    """A presentation-neutral copy of the learned model."""

    kind: LearnedKind
    boundary_hours: float | None = None


class Topic(Enum):
    """The part of the application model that changed."""

    FOLDER = auto()
    OPTIONS = auto()
    PATTERNS = auto()
    PREVIEW = auto()
    SELECTION = auto()
    DRAFT = auto()
    STATUS = auto()
    ACTIONS = auto()
    LANGUAGE = auto()
    LOGGING = auto()
    SORT = auto()
    BUSY = auto()


@dataclass(frozen=True, slots=True)
class ChooseStatus:
    failed: bool = False


@dataclass(frozen=True, slots=True)
class SummaryStatus:
    events: int
    files: int
    missing: int
    event_folders: int
    other_folders: int
    learned: LearnedSummary
    left_out: int
    failed: bool = False


@dataclass(frozen=True, slots=True)
class OptionProblemStatus:
    fault: OptionFault
    field: OptionField
    low: int | None = None
    high: int | None = None
    failed: bool = True


@dataclass(frozen=True, slots=True)
class ValueProblemStatus:
    message: str
    failed: bool = True


@dataclass(frozen=True, slots=True)
class ReadFailureStatus:
    path: Path
    error: BaseException
    failed: bool = True


@dataclass(frozen=True, slots=True)
class PreviewStaysStatus:
    files: int
    events: int
    failed: bool = False


Status = (
    ChooseStatus
    | SummaryStatus
    | OptionProblemStatus
    | ValueProblemStatus
    | ReadFailureStatus
    | PreviewStaysStatus
)


@dataclass(frozen=True, slots=True)
class DayInfo:
    """What happened on one calendar day. A later event replaces an earlier one."""

    files: int
    cluster: int | None


@dataclass(frozen=True, slots=True)
class ShownFile:
    """One file the window can place on a timeline."""

    timestamp: datetime
    name: str


@dataclass(frozen=True, slots=True)
class ShownEvent:
    """One event the window can draw, without a core cluster object."""

    number: int
    name: str
    start: datetime
    end: datetime
    files: tuple[ShownFile, ...]


def as_shown(result) -> tuple[ShownEvent, ...]:
    """Copy a preview into draw values. ``None`` is an empty preview."""

    if result is None:
        return ()
    return tuple(
        ShownEvent(
            cluster.number,
            cluster.name,
            cluster.start,
            cluster.end,
            tuple(ShownFile(item.timestamp, item.name) for item in cluster.files),
        )
        for cluster in result.clusters
    )


def cover_days(events) -> dict[date, DayInfo]:
    """Map each day inside an event to its file count and event index.

    Days between an event's first and last photo are included with zero files.
    When two events share a day, the later event is the one that owns it.
    """

    days: dict[date, DayInfo] = {}
    for index, event in enumerate(events):
        if not event.files:
            continue
        counts: dict[date, int] = {}
        for item in event.files:
            day = item.timestamp.date()
            counts[day] = counts.get(day, 0) + 1
        day = event.start.date()
        while day <= event.end.date():
            days[day] = DayInfo(files=counts.get(day, 0), cluster=index)
            day += timedelta(days=1)
    return days


trace_module(sys.modules[__name__])
