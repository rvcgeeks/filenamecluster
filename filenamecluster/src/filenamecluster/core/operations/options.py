"""Turn option text into clustering inputs.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import sys
from datetime import timedelta

from filenamecluster.core.algorithm.cluster import ClusterParams
from filenamecluster.core.algorithm import ModelOptions
from filenamecluster.core.parser import LIMIT_FIELDS, PatternRule, TimestampPatterns
from filenamecluster.log import trace_module
from .errors import OptionError, OptionFault, OptionField


def rule_error(description: str, source: str) -> str:
    """The parser message when one expression cannot be compiled.

    A blank expression is turned off, so it is not an error.
    """

    if not str(source).strip():
        return ""
    try:
        TimestampPatterns(rules=(PatternRule("", description, source),)).compile()
    except ValueError as exc:
        return str(exc)
    return ""


class OptionReader:
    """Accept or refuse option text. It does not draw and it does not translate."""

    def read(
        self,
        hours: dict[str, str],
        limits: dict[str, str],
        rows: list[tuple],
    ) -> tuple[ClusterParams, TimestampPatterns, tuple[str, ...]]:
        """Build the objects a preview scans with, or raise ``OptionError`` or ``ValueError``.

        A row whose expression cannot be compiled is left out of the patterns.
        Its id is returned last so the caller can mark it.
        """

        floor = self._number(OptionField.FLOOR, hours["floor"])
        ceiling = self._number(OptionField.CEILING, hours["ceiling"])
        parsed: dict[str, int] = {}
        for key, _label, _hint, low, high in LIMIT_FIELDS:
            parsed[key] = self._whole(_LIMIT_FIELDS[key], limits[key], low, high)
        params = ClusterParams(
            floor=timedelta(hours=floor),
            ceiling=timedelta(hours=ceiling),
        )
        rules = []
        invalid: list[str] = []
        for iid, key, description, pattern, *_rest in rows:
            if rule_error(description, pattern):
                invalid.append(str(iid))
                continue
            rules.append(PatternRule(str(key), description, pattern))
        patterns = TimestampPatterns(rules=tuple(rules), **parsed)
        patterns.compile()
        return params, patterns, tuple(invalid)

    def accepts(self, options: ModelOptions) -> bool:
        """Whether a saved options object can be compiled."""

        hours = {
            "floor": str(options.floor_hours),
            "ceiling": str(options.ceiling_hours),
        }
        limits = {key: str(getattr(options, key)) for key, *_rest in LIMIT_FIELDS}
        rows = [
            (key or f"row-{index}", key, description, pattern, False)
            for index, (key, description, pattern) in enumerate(options.rules)
        ]
        try:
            self.read(hours, limits, rows)
        except (OptionError, OverflowError, TypeError, ValueError):
            return False
        return True

    @staticmethod
    def _number(field: OptionField, raw: str) -> float:
        try:
            return float(raw)
        except (TypeError, ValueError):
            raise OptionError(OptionFault.NOT_A_NUMBER, field) from None

    @staticmethod
    def _whole(field: OptionField, raw: str, low: int, high: int) -> int:
        try:
            value = int(str(raw).strip())
        except (TypeError, ValueError):
            raise OptionError(OptionFault.NOT_WHOLE, field) from None
        if not low <= value <= high:
            raise OptionError(OptionFault.OUT_OF_RANGE, field, low, high)
        return value


_LIMIT_FIELDS = {
    "min_year": OptionField.MIN_YEAR,
    "max_year": OptionField.MAX_YEAR,
    "prec_clock": OptionField.PREC_CLOCK,
    "prec_epoch": OptionField.PREC_EPOCH,
    "prec_date": OptionField.PREC_DATE,
}


trace_module(sys.modules[__name__])
