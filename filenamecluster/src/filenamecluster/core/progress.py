"""How far a disk job has got, so the window can draw a progress bar.

The bar's thread sets the meter before the work starts. Scan, preview, and
move call ``expect`` and ``tick``. A job that never reports a total leaves
the bar moving without a fraction.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import sys
import threading
from contextvars import ContextVar, Token

from filenamecluster.log import trace_module


class Meter:
    """A count of finished steps and the count the job said it would take."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.done = 0
        self.total = 0

    def add(self, count: int) -> None:
        with self._lock:
            self.total += max(int(count), 0)

    def advance(self, count: int = 1) -> None:
        with self._lock:
            self.done += max(int(count), 0)
            if self.total and self.done > self.total:
                self.done = self.total

    def read(self) -> tuple[int, int]:
        with self._lock:
            return self.done, self.total


_meter: ContextVar[Meter | None] = ContextVar("filenamecluster_meter", default=None)


def bind(meter: Meter) -> Token:
    """Make ``meter`` the one ``expect`` and ``tick`` update on this thread."""

    return _meter.set(meter)


def unbind(token: Token) -> None:
    _meter.reset(token)


def expect(count: int) -> None:
    """Add ``count`` steps to the total. No meter means the call does nothing."""

    meter = _meter.get()
    if meter is not None and count:
        meter.add(count)


def tick(count: int = 1) -> None:
    """Mark ``count`` steps finished. No meter means the call does nothing."""

    meter = _meter.get()
    if meter is not None and count:
        meter.advance(count)


trace_module(sys.modules[__name__])
