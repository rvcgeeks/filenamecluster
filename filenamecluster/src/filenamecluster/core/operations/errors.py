"""Errors raised when an option cannot be used.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import sys
from enum import Enum, auto

from filenamecluster.log import trace_module


class OptionFault(Enum):
    """Why one option value was refused. The view chooses the sentence."""

    NOT_A_NUMBER = auto()
    NOT_WHOLE = auto()
    OUT_OF_RANGE = auto()


class OptionField(Enum):
    """Which option value was refused. The view chooses its label."""

    FLOOR = auto()
    CEILING = auto()
    MIN_YEAR = auto()
    MAX_YEAR = auto()
    PREC_CLOCK = auto()
    PREC_EPOCH = auto()
    PREC_DATE = auto()


class OptionError(Exception):
    """An option field is missing, not a number, or outside its allowed range."""

    def __init__(
        self,
        fault: OptionFault,
        field: OptionField,
        low: int | None = None,
        high: int | None = None,
    ) -> None:
        self.fault = fault
        self.field = field
        self.low = low
        self.high = high
        super().__init__(fault.name)


trace_module(sys.modules[__name__])
