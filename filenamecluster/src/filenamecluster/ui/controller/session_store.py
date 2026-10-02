"""Write options and the learned boundary when the window closes.

A side that matches the model file is left as it is. A number that cannot
be read does not replace the options already stored.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import sys

from filenamecluster.core.operations import OptionError, OptionReader, RuleLedger, rule_error, store_if_changed
from filenamecluster.log import event, trace_module


class SessionStore:
    """Compare the session with ``filenamecluster-model.json`` and write a change."""

    def __init__(self, model) -> None:
        self.model = model

    def store(self) -> None:
        directory = self.model.directory
        if directory is None:
            return
        options = self._options()
        result = self.model.result
        learned = result.model if result is not None else None
        try:
            wrote = store_if_changed(directory, learned, options)
        except OSError:
            event("model_save_failed", path=str(directory))
            return
        if not wrote or options is None:
            return
        RuleLedger.mark(
            directory,
            [
                (key, description, pattern, bool(rule_error(description, pattern)))
                for _iid, key, description, pattern, _dirty in self.model.pattern_table()
            ],
        )

    def _options(self):
        try:
            return OptionReader().stored(
                self.model.option_drafts(),
                self.model.limit_drafts(),
                self.model.pattern_table(),
            )
        except (OptionError, KeyError, OverflowError, TypeError, ValueError):
            return None


trace_module(sys.modules[__name__])
