"""One filename the destination already has, and what the user decides.

The view writes the choice. The controller reads it. Neither this class
nor its fields know about widgets.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from enum import Enum, auto

from filenamecluster.log import trace_module


class ClashChoice(Enum):
    """What to do with one filename the destination already has."""

    REPLACE = auto()
    SKIP = auto()


@dataclass
class NameClash:
    """The destination already has a file with this name.

    ``count`` is how many clashes this answer can still cover, including
    this one. The dialog writes ``choice``, ``for_all``, and ``cancelled``.
    """

    name: str
    count: int
    choice: ClashChoice | None = None
    for_all: bool = False
    cancelled: bool = False


trace_module(sys.modules[__name__])
