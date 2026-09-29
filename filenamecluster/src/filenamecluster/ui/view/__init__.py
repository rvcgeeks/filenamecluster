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
from .spinner import SpinnerDialog, gif_delays, gif_frames, spinner_path
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
    "AppView",
    "Dialogs",
    "SpinnerDialog",
    "TimeScale",
    "axis_ticks",
    "backing_scale",
    "describe_model",
    "describe_zoom",
    "file_count",
    "file_marks",
    "fit_pixels_per_day",
    "gif_delays",
    "gif_frames",
    "layout_bars",
    "month_weeks",
    "prepare_process_dpi",
    "sections",
    "shift_month",
    "spinner_path",
    "t",
    "use_script",
]
