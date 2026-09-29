"""Keep invalid filename rules in the model file after a scan.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

from filenamecluster.log import trace_module
from .model import keep_rules


class RuleLedger:
    """Put every pattern row back into ``options.rules``, with invalid rows marked.

    The scan only receives the rows that compile, so ``save_model`` stores only
    those. This puts the others back. ``model.py`` performs the write.
    """

    @staticmethod
    def mark(directory: Path, rows: Sequence[tuple[str, str, str, bool]]) -> None:
        """``rows`` are ``(key, description, pattern, invalid)`` in table order."""

        keep_rules(directory, rows)


trace_module(sys.modules[__name__])
