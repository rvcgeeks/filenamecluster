"""Built-in option rows. The session stores values a preview has accepted.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import sys
from datetime import timedelta

from filenamecluster.core.algorithm.cluster import ClusterParams
from filenamecluster.core.parser import LIMIT_FIELDS
from filenamecluster.log import trace_module


class OptionFields:
    """The safety-limit rows and the conversion from a pause to hours."""

    DEFAULTS = ClusterParams()
    # key, label key, hint key, (lowest, highest, step)
    FIELDS = (
        ("floor", "floor_label", "floor_hint", (0.5, 168, 0.5)),
        ("ceiling", "ceiling_label", "ceiling_hint", (1, 8760, 1)),
    )
    LIMITS = LIMIT_FIELDS

    @staticmethod
    def hours(delta: timedelta) -> float:
        """Length of ``delta`` in hours."""

        return delta.total_seconds() / 3600


trace_module(sys.modules[__name__])
