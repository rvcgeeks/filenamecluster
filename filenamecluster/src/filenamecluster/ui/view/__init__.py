"""The window and the words and drawings on it.

Other packages import these names from ``filenamecluster.ui.view``.
They do not import the modules inside this package directly.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from .about import sections
from .calendar import month_weeks, shift_month
from .dialogs import Dialogs
from .i18n import (
    CATALOGS,
    LANGUAGES,
    describe_model,
    file_count,
    t,
)
from .layout import (
    MAX_WIDTH,
    MIN_BAR,
    MIN_PIXELS_PER_DAY,
    MARGIN,
    TimeScale,
    axis_ticks,
    file_marks,
    fit_pixels_per_day,
    layout_bars,
)
from .progress_bar import ProgressDialog, bar_span, release_wait
from .prompt import PROMPT_TIMEOUT_SECONDS
from .theme import backing_scale, prepare_process_dpi, use_script
from .timeline_draw import describe_zoom
from .view import AppView

__all__ = [
    "CATALOGS",
    "LANGUAGES",
    "MAX_WIDTH",
    "MIN_BAR",
    "MIN_PIXELS_PER_DAY",
    "MARGIN",
    "PROMPT_TIMEOUT_SECONDS",
    "AppView",
    "ProgressDialog",
    "Dialogs",
    "TimeScale",
    "axis_ticks",
    "backing_scale",
    "bar_span",
    "describe_model",
    "describe_zoom",
    "file_count",
    "file_marks",
    "fit_pixels_per_day",
    "layout_bars",
    "month_weeks",
    "prepare_process_dpi",
    "release_wait",
    "sections",
    "shift_month",
    "t",
    "use_script",
]
