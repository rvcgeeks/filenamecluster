"""Apply the session's logging choice to the logging service.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import sys

from filenamecluster.log import set_logging_enabled, trace_module


class SystemLogging:
    """The logging service behind ``LoggingPort``."""

    def apply(self, enabled: bool) -> None:
        set_logging_enabled(bool(enabled))


trace_module(sys.modules[__name__])
