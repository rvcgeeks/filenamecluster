"""Group files into events by the timestamp gaps in one folder.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Mathematics: ``docs/algorithm.md``. Design: ``docs/architecture.md``.

The split point is learned from those gaps. A short pause and a long pause
are two patterns. A pause joins the event when it looks like the short
pattern, and starts a new event when it looks like the long one. Two safety
limits stay fixed: a very short pause never starts a new event, and a very
long one always does.
"""

from __future__ import annotations

import sys
from filenamecluster.log import detail, trace_module

import math
from dataclasses import dataclass
from datetime import timedelta

from filenamecluster.core.parser import TimestampedFile

from .fit import GapModel, fit
from .split import FALLBACK_HOURS, split as pause_split


@dataclass(frozen=True, slots=True)
class ModelOptions:
    """Safety limits, year window, priorities, and filename rules for one folder.

    Saved beside the fitted boundary. Fitting and reusing that boundary does
    not read this object.
    """

    floor_hours: float
    ceiling_hours: float
    min_year: int
    max_year: int
    prec_clock: int
    prec_epoch: int
    prec_date: int
    rules: tuple[tuple[str, str, str], ...]


@dataclass(frozen=True, slots=True)
class FolderModel:
    """The boundary and options last written for one folder."""

    learned: GapModel | None = None
    options: ModelOptions | None = None

    def with_learned(self, learned: GapModel | None) -> FolderModel:
        """Replace the boundary and keep the saved options."""

        return FolderModel(learned, self.options)

    def with_options(self, options: ModelOptions | None) -> FolderModel:
        """Replace the saved options and keep the boundary."""

        return FolderModel(self.learned, options)


@dataclass(frozen=True, slots=True)
class ClusterParams:
    """Safety limits around the learned boundary.

    ``floor`` is never split. ``ceiling`` is always split. Everything between
    them follows the patterns learned from this folder's timestamps.
    """

    floor: timedelta = timedelta(hours=3)
    ceiling: timedelta = timedelta(days=30)

    def __post_init__(self) -> None:
        if self.floor <= timedelta(0):
            raise ValueError("floor must be positive")
        if self.ceiling <= self.floor:
            raise ValueError("ceiling must be greater than floor")

    @property
    def floor_hours(self) -> float:
        return self.floor.total_seconds() / 3600

    @property
    def ceiling_hours(self) -> float:
        return self.ceiling.total_seconds() / 3600


@dataclass(frozen=True, slots=True)
class Cluster:
    """One event: files in chronological order."""

    files: tuple[TimestampedFile, ...]

    @property
    def start(self):
        return self.files[0].timestamp

    @property
    def end(self):
        return self.files[-1].timestamp


def cluster(
    files: list[TimestampedFile] | tuple[TimestampedFile, ...],
    params: ClusterParams | None = None,
    model: FolderModel | None = None,
) -> tuple[list[Cluster], GapModel | None]:
    """Cluster ``files`` by capture time and return the learned gap pattern.

    Input order does not matter. Equal timestamps stay together and are
    ordered by filename. When this folder does not have enough pauses to refit,
    ``model`` supplies the boundary already learned.
    """

    chosen = params or ClusterParams()
    corrections = model or FolderModel()
    ordered = tuple(sorted(files, key=lambda item: (item.timestamp, item.name)))
    detail(
        "files_ordered",
        count=len(ordered),
        floor_hours=chosen.floor_hours,
        ceiling_hours=chosen.ceiling_hours,
    )
    if not ordered:
        detail("cluster_empty")
        return [], None
    if len(ordered) == 1:
        detail("cluster_single", name=ordered[0].name, stamp=ordered[0].timestamp.isoformat(sep=" "))
        return [Cluster(ordered)], None

    gaps = [
        (ordered[index + 1].timestamp - ordered[index].timestamp).total_seconds() / 3600
        for index in range(len(ordered) - 1)
    ]
    unlabeled = [
        math.log(hours)
        for hours in gaps
        if chosen.floor_hours < hours < chosen.ceiling_hours
    ]
    detail(
        "gaps_measured",
        count=len(gaps),
        unlabeled=len(unlabeled),
        shortest=min(gaps),
        longest=max(gaps),
    )
    learned = fit(unlabeled)
    if learned is None and corrections.learned is not None:
        # A handful of new photos is not enough to refit. Keep the boundary
        # this folder already learned, and refit once more pauses exist.
        learned = corrections.learned
        detail(
            "boundary_reused",
            boundary_hours=learned.boundary_hours,
            within_hours=learned.within_hours,
            between_hours=learned.between_hours,
            separated=learned.separated,
        )
    elif learned is None:
        detail("boundary_fallback", split_hours=FALLBACK_HOURS, ceiling_hours=chosen.ceiling_hours)
    else:
        detail(
            "boundary_fitted",
            boundary_hours=learned.boundary_hours,
            within_hours=learned.within_hours,
            between_hours=learned.between_hours,
            separated=learned.separated,
        )

    groups: list[list[TimestampedFile]] = [[ordered[0]]]
    for index, hours in enumerate(gaps):
        previous = ordered[index]
        nxt = ordered[index + 1]
        boundary = None if learned is None else learned.boundary_hours
        split = pause_split(hours, chosen.floor_hours, chosen.ceiling_hours, boundary)
        if boundary is None:
            # Too few pauses to fit two patterns. Keep same-day and next-day
            # shooting together, and split a pause of a day and a half or more.
            reason = "fallback"
        elif hours <= chosen.floor_hours:
            reason = "floor"
        elif hours >= chosen.ceiling_hours:
            reason = "ceiling"
        else:
            reason = "boundary"
        detail(
            "gap_decision",
            index=index,
            hours=hours,
            split=split,
            reason=reason,
            left=previous.name,
            right=nxt.name,
        )
        if split:
            groups.append([nxt])
        else:
            groups[-1].append(nxt)
    detail("clusters_formed", count=len(groups), sizes=[len(group) for group in groups])
    return [Cluster(tuple(group)) for group in groups], learned

trace_module(sys.modules[__name__])
