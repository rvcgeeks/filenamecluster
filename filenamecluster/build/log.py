"""Debug logging for the build, written to stderr so CI keeps every line.

The logger is ``build``. Each line has the time, the level, and the module.
It is always at DEBUG: a release build is the log we read when it fails.
"""

from __future__ import annotations

import logging
import sys

NAME = "build"
_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


class _StderrHandler(logging.StreamHandler):
    """Write to the current ``sys.stderr``, including one a test replaces."""

    def emit(self, record: logging.LogRecord) -> None:
        self.stream = sys.stderr
        super().emit(record)


def configure() -> logging.Logger:
    """Attach one stderr handler. Later calls keep that handler."""

    logger = logging.getLogger(NAME)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    if not any(isinstance(handler, _StderrHandler) for handler in logger.handlers):
        handler = _StderrHandler()
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(logging.Formatter(_FORMAT))
        logger.addHandler(handler)
    return logger


def get_logger(name: str) -> logging.Logger:
    """A ``build`` logger. ``name`` is the module, such as ``build.tcl``."""

    configure()
    return logging.getLogger(name)
