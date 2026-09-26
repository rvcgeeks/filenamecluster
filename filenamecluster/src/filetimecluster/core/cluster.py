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

import math
from dataclasses import dataclass
from datetime import timedelta

from filetimecluster.core.learn import GapModel, fit_gap_model
from filetimecluster.core.model_file import FolderModel
from filetimecluster.core.parse import TimestampedFile


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


def cluster_files(
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
    if not ordered:
        return [], None
    if len(ordered) == 1:
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
    learned = fit_gap_model(unlabeled)
    if learned is None and corrections.learned is not None:
        # A handful of new photos is not enough to refit. Keep the boundary
        # this folder already learned, and refit once more pauses exist.
        learned = corrections.learned

    groups: list[list[TimestampedFile]] = [[ordered[0]]]
    for index, hours in enumerate(gaps):
        if learned is None:
            # Too few pauses to fit two patterns. Keep same-day and next-day
            # shooting together, and split a pause of a day and a half or more.
            split = hours >= chosen.ceiling_hours or hours >= 36
        else:
            split = learned.splits(hours, chosen.floor_hours, chosen.ceiling_hours)
        if split:
            groups.append([ordered[index + 1]])
        else:
            groups[-1].append(ordered[index + 1])
    return [Cluster(tuple(group)) for group in groups], learned
