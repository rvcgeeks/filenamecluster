"""Session state for one window. Widgets live in the view.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

from filenamecluster.core.cluster import ClusterParams
from filenamecluster.core.learn import MODEL_NAME
from filenamecluster.core.parse import TimestampedFile
from filenamecluster.core.pipeline import ClusterResult
from filenamecluster.log import trace_module
from filenamecluster.ui.model.i18n import t

DEFAULTS = ClusterParams()

# key, label key, hint key, (lowest, highest, step)
OPTIONS = (
    ("floor", "floor_label", "floor_hint", (0.5, 168, 0.5)),
    ("ceiling", "ceiling_label", "ceiling_hint", (1, 8760, 1)),
)


def hours(delta: timedelta) -> float:
    """Length of ``delta`` in hours."""

    return delta.total_seconds() / 3600


def describe_model(model: object) -> str:
    """One status-line sentence for the learned boundary, or for its absence."""

    if model is None:
        return t("model_none", name=MODEL_NAME)
    separated = bool(getattr(model, "separated", False))
    if not separated:
        return t("model_one", name=MODEL_NAME)
    boundary = float(getattr(model, "boundary_hours", 0))
    return t("model_learned", hours=f"{boundary:.0f}", name=MODEL_NAME)


class AppModel:
    """The folder, the last preview, and what the user has selected.

    Option numbers and filename rules are edited in the view and stored in
    ``filenamecluster-model.json`` beside ``learned``. This object does not
    decide where an event boundary is.
    """

    def __init__(self) -> None:
        self.directory: Path | None = None
        self.result: ClusterResult | None = None
        self.selected_cluster: int | None = None
        self.selected_day: date | None = None
        self.files_by_day: dict[date, list[tuple[TimestampedFile, int]]] = {}
        self.cluster_sort: tuple[str, bool] | None = None
        self.pattern_desc_dirty: set[str] = set()
        self.custom_pattern_seq: int = 1
        self.status_builder = lambda: (t("choose_status"), False)


trace_module(sys.modules[__name__])
