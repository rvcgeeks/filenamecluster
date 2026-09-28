"""Place clusters and axis ticks on a to-scale time axis.

Author: Rajas Chavadekar (rvchavadekar@gmail.com). Design: ``docs/architecture.md``.

Pure geometry with no Tk, so it can be tested on its own. One day always
spans ``pixels_per_day`` pixels, so the distance between two events on screen
is proportional to the real time between them.
"""

from __future__ import annotations

import sys
from filenamecluster.log import trace_module

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterator, Sequence

from filenamecluster.core.organize import NamedCluster

SECONDS_PER_DAY = 86_400
MARGIN = 48
MIN_BAR = 4
LANE_GAP = 6
CHAR_WIDTH = 8
MIN_PIXELS_PER_DAY = 0.02
MAX_PIXELS_PER_DAY = 20_000.0
MAX_WIDTH = 1_000_000
MIN_SPAN = timedelta(hours=1)


@dataclass(frozen=True, slots=True)
class Bar:
    """Where one cluster is drawn: its x range and the lane (row) it sits in."""

    index: int
    x0: float
    x1: float
    lane: int


@dataclass(frozen=True, slots=True)
class Tick:
    """One axis mark. Major ticks carry a label and a grid line."""

    x: float
    label: str
    major: bool


class TimeScale:
    """Map datetimes to canvas x positions at a fixed number of pixels per day."""

    def __init__(self, start: datetime, end: datetime, pixels_per_day: float) -> None:
        if end < start:
            raise ValueError("end must not be before start")
        self.start = start
        self.end = max(end, start + MIN_SPAN)
        self.pixels_per_day = clamp_pixels_per_day(pixels_per_day, start, end)

    @property
    def width(self) -> float:
        return self.x(self.end) + MARGIN

    def x(self, when: datetime) -> float:
        days = (when - self.start).total_seconds() / SECONDS_PER_DAY
        return MARGIN + days * self.pixels_per_day

    def when(self, x: float) -> datetime:
        days = (x - MARGIN) / self.pixels_per_day
        return self.start + timedelta(days=days)


def span_days(start: datetime, end: datetime) -> float:
    return max(end - start, MIN_SPAN).total_seconds() / SECONDS_PER_DAY


def clamp_pixels_per_day(value: float, start: datetime, end: datetime) -> float:
    """Keep the zoom inside sane limits and the whole timeline under MAX_WIDTH."""

    widest = (MAX_WIDTH - 2 * MARGIN) / span_days(start, end)
    return max(MIN_PIXELS_PER_DAY, min(value, MAX_PIXELS_PER_DAY, widest))


def fit_pixels_per_day(start: datetime, end: datetime, width: float) -> float:
    """Zoom level at which the whole span fits in ``width`` pixels."""

    usable = max(width - 2 * MARGIN, 1)
    return clamp_pixels_per_day(usable / span_days(start, end), start, end)


def layout_bars(clusters: Sequence[NamedCluster], scale: TimeScale) -> list[Bar]:
    """Give each cluster an x range and the first lane where it does not overlap.

    The number label drawn at the left of each bar counts as part of its
    width, so labels never collide either.
    """

    lane_ends: list[float] = []
    bars: list[Bar] = []
    for index, cluster in enumerate(clusters):
        if cluster.end < scale.start or cluster.start > scale.end:
            continue
        x0 = scale.x(max(cluster.start, scale.start))
        x1 = max(scale.x(min(cluster.end, scale.end)), x0 + MIN_BAR)
        reach = max(x1, x0 + CHAR_WIDTH * len(str(cluster.number)) + 6)
        lane = next(
            (row for row, end in enumerate(lane_ends) if end + LANE_GAP <= x0),
            len(lane_ends),
        )
        if lane == len(lane_ends):
            lane_ends.append(reach)
        else:
            lane_ends[lane] = reach
        bars.append(Bar(index=index, x0=x0, x1=x1, lane=lane))
    return bars


def file_marks(clusters: Sequence[NamedCluster], scale: TimeScale) -> list[int]:
    """Distinct pixel columns inside the scale that hold at least one file."""

    return sorted(
        {
            round(scale.x(item.timestamp))
            for cluster in clusters
            for item in cluster.files
            if scale.start <= item.timestamp <= scale.end
        }
    )


def axis_ticks(scale: TimeScale) -> list[Tick]:
    """Ticks for the visible zoom: years, then months, then days, then hours."""

    ppd = scale.pixels_per_day
    start, end = scale.start, scale.end
    if ppd >= 60:
        major = [(when, f"{when:%d-%m-%Y}") for when in _every(start, end, timedelta(days=1))]
        step = timedelta(hours=1) if ppd >= 240 else timedelta(hours=6)
        minor = list(_every(start, end, step))
    elif ppd >= 1.5:
        major = [(when, f"{when:%b %Y}") for when in _month_starts(start, end)]
        minor = list(_every(start, end, timedelta(days=1))) if ppd >= 6 else []
    else:
        every = max(1, round(60 / (365 * ppd)))
        major = [
            (when, f"{when:%Y}")
            for when in _year_starts(start, end)
            if when.year % every == 0
        ]
        minor = list(_month_starts(start, end)) if ppd >= 0.2 else []

    ticks = [Tick(scale.x(when), label, True) for when, label in major]
    taken = {round(tick.x) for tick in ticks}
    ticks.extend(
        Tick(scale.x(when), "", False)
        for when in minor
        if round(scale.x(when)) not in taken
    )
    return sorted(
        (tick for tick in ticks if 0 <= tick.x <= scale.width),
        key=lambda tick: tick.x,
    )


def _every(start: datetime, end: datetime, step: timedelta) -> Iterator[datetime]:
    current = datetime(start.year, start.month, start.day)
    while current <= end:
        yield current
        current += step


def _month_starts(start: datetime, end: datetime) -> Iterator[datetime]:
    current = datetime(start.year, start.month, 1)
    while current <= end:
        yield current
        current = datetime(
            current.year + current.month // 12, current.month % 12 + 1, 1
        )


def _year_starts(start: datetime, end: datetime) -> Iterator[datetime]:
    for year in range(start.year, end.year + 1):
        yield datetime(year, 1, 1)

trace_module(sys.modules[__name__])
