"""One filename rule held by the session.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import sys
from typing import NamedTuple

from filenamecluster.core import rule_error
from filenamecluster.log import trace_module


class PatternSnapshot(NamedTuple):
    """A copy of one pattern row. Changing it does not change the session."""

    iid: str
    key: str
    description: str
    pattern: str
    dirty: bool
    invalid: bool


class PatternRow:
    """One filename rule held by the session.

    ``invalid`` is true when the expression cannot be compiled. A blank
    expression is turned off, so it is not invalid. ``dirty`` is true when a
    built-in description no longer matches the built-in wording.
    """

    def __init__(self, iid: str, key: str, description: str, pattern: str, dirty: bool) -> None:
        self.iid = iid
        self.key = key
        self.description = description
        self.pattern = pattern
        self.dirty = dirty
        self.invalid = bool(rule_error(description, pattern))


trace_module(sys.modules[__name__])
