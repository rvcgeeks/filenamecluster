"""Session state and the built-in option rows.

Other packages import these names from ``filenamecluster.ui.model``.
They do not import the modules inside this package directly.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from .clash import ClashChoice, NameClash
from .display import (
    ChooseStatus,
    DayInfo,
    LearnedKind,
    LearnedSummary,
    OptionProblemStatus,
    PreviewStaysStatus,
    ReadFailureStatus,
    SkippedReason,
    SummaryStatus,
    Topic,
    ValueProblemStatus,
    cover_days,
)
from .options import OptionFields
from .patterns import PatternRow, PatternSnapshot
from .model import AppModel

__all__ = [
    "AppModel",
    "ChooseStatus",
    "ClashChoice",
    "NameClash",
    "DayInfo",
    "LearnedKind",
    "LearnedSummary",
    "OptionFields",
    "OptionProblemStatus",
    "PatternRow",
    "PatternSnapshot",
    "PreviewStaysStatus",
    "ReadFailureStatus",
    "SkippedReason",
    "SummaryStatus",
    "Topic",
    "ValueProblemStatus",
    "cover_days",
]
