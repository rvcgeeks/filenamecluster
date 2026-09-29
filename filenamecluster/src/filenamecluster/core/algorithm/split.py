"""Decide whether one pause starts a new event.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
The derivation is ``docs/algorithm.md``, section 7.

A pause at or below the floor stays in the event. A pause at or above the
ceiling starts a new one. Between them, the learned boundary decides. With
no boundary, a pause of a day and a half or more starts a new event.
"""

from __future__ import annotations

import sys

from filenamecluster.log import trace_module

FALLBACK_HOURS = 36


def split(
    hours: float,
    floor_hours: float,
    ceiling_hours: float,
    boundary_hours: float | None,
) -> bool:
    """Whether a pause of ``hours`` should start a new event.

    ``boundary_hours`` is ``None`` when this folder has no fitted or saved boundary.
    """

    if boundary_hours is None:
        return hours >= ceiling_hours or hours >= FALLBACK_HOURS
    if hours <= floor_hours:
        return False
    if hours >= ceiling_hours:
        return True
    return hours >= boundary_hours


trace_module(sys.modules[__name__])
