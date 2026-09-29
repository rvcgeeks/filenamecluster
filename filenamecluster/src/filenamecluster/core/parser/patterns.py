"""Filename patterns: the built-in rules and how one row is compiled.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass

from filenamecluster.log import trace_module

# Higher wins when several stamps sit in one name. A camera-style
# YYYYMMDD_HHMMSS beats a trailing epoch (often an export id) and a bare date.
# kind, groups that must be named, groups that may also be named
_KIND_SPECS = (
    ("clock", frozenset({"y", "mo", "d", "h", "mi", "s"}), frozenset({"ms"})),
    ("numeric_date", frozenset({"a", "b", "y", "h", "mi"}), frozenset({"s"})),
    ("epoch_ms", frozenset({"ms"}), frozenset()),
    ("date_only", frozenset({"y", "mo", "d"}), frozenset()),
)

# key, label, example filename, named groups the expression must provide
PATTERN_FIELDS = (
    (
        "clock_separated",
        "Dashed clock",
        "2024-01-01-10-15-00",
        "y, mo, d, h, mi, s; optional ms",
    ),
    (
        "clock_compact_sep",
        "Compact clock",
        "IMG_20240101_101500",
        "y, mo, d, h, mi, s; optional ms",
    ),
    (
        "clock_compact_17",
        "17-digit clock",
        "20240101101500123",
        "y, mo, d, h, mi, s; optional ms",
    ),
    (
        "clock_compact_14",
        "14-digit clock",
        "20240101101500",
        "y, mo, d, h, mi, s",
    ),
    (
        "numeric_date",
        "Day-month clock",
        "CamScanner 11-21-2024 12.22",
        "a, b, y, h, mi; optional s",
    ),
    ("epoch_ms", "Unix milliseconds", "img1462863402727", "ms"),
    ("date_only", "Date only", "IMG-20240101-WA0001", "y, mo, d"),
)

@dataclass(frozen=True, slots=True)
class PatternRule:
    """One filename expression. A blank ``pattern`` is turned off.

    ``key`` identifies a built-in rule. A rule added in the table may use an
    empty key. ``description`` is the label shown for that row.
    """

    key: str
    description: str
    pattern: str


def _builtin_rules() -> tuple[PatternRule, ...]:
    sources = {
        "clock_separated": (
            r"(?<!\d)(?P<y>\d{4})-(?P<mo>\d{2})-(?P<d>\d{2})-"
            r"(?P<h>\d{2})-(?P<mi>\d{2})-(?P<s>\d{2})(?:-(?P<ms>\d{3}))?"
        ),
        "clock_compact_sep": (
            r"(?<!\d)(?P<y>\d{4})(?P<mo>\d{2})(?P<d>\d{2})[_-]"
            r"(?P<h>\d{2})(?P<mi>\d{2})(?P<s>\d{2})(?P<ms>\d{1,3})?(?!\d)"
        ),
        "clock_compact_17": (
            r"(?<!\d)(?P<y>\d{4})(?P<mo>\d{2})(?P<d>\d{2})"
            r"(?P<h>\d{2})(?P<mi>\d{2})(?P<s>\d{2})(?P<ms>\d{3})(?!\d)"
        ),
        "clock_compact_14": (
            r"(?<!\d)(?P<y>\d{4})(?P<mo>\d{2})(?P<d>\d{2})"
            r"(?P<h>\d{2})(?P<mi>\d{2})(?P<s>\d{2})(?!\d)"
        ),
        "numeric_date": (
            r"(?<!\d)(?P<a>\d{1,2})-(?P<b>\d{1,2})-(?P<y>\d{4})\s+"
            r"(?P<h>\d{2})[.:](?P<mi>\d{2})(?:[.:](?P<s>\d{2}))?"
        ),
        "epoch_ms": r"(?<!\d)(?P<ms>\d{13})(?!\d)",
        "date_only": r"(?<!\d)(?P<y>\d{4})[-_]?(?P<mo>\d{2})[-_]?(?P<d>\d{2})(?!\d)",
    }
    return tuple(
        PatternRule(key, label, sources[key]) for key, label, _example, _groups in PATTERN_FIELDS
    )


DEFAULT_RULES = _builtin_rules()
_RULE_KEYS = {rule.key for rule in DEFAULT_RULES}

# key, label, hint, lowest, highest
LIMIT_FIELDS = (
    ("min_year", "Minimum year", "A stamp before this year is ignored.", 1, 9999),
    ("max_year", "Maximum year", "A stamp after this year is ignored.", 1, 9999),
    (
        "prec_clock",
        "Clock priority",
        "Higher wins when one name also matches an epoch or a bare date.",
        0,
        1000,
    ),
    (
        "prec_epoch",
        "Epoch priority",
        "Priority of a Unix millisecond stamp.",
        0,
        1000,
    ),
    (
        "prec_date",
        "Date priority",
        "Priority of a date that has no time.",
        0,
        1000,
    ),
)


@dataclass(frozen=True, slots=True, init=False)
class TimestampPatterns:
    """Filename rules and the year window and priorities they are judged with.

    ``rules`` starts as the built-in rows. Pass a longer tuple to recognise
    more names. A blank expression is turned off. Keyword arguments named
    after a built-in key replace that row's expression, which is how the
    original fixed fields still work.
    """

    rules: tuple[PatternRule, ...]
    min_year: int
    max_year: int
    prec_clock: int
    prec_epoch: int
    prec_date: int

    def __init__(
        self,
        rules: Sequence[PatternRule] | None = None,
        *,
        min_year: int = 1990,
        max_year: int = 2100,
        prec_clock: int = 30,
        prec_epoch: int = 20,
        prec_date: int = 10,
        **overrides: str,
    ) -> None:
        unknown = set(overrides) - _RULE_KEYS
        if unknown:
            names = ", ".join(sorted(unknown))
            raise TypeError(f"unexpected pattern fields: {names}")
        chosen = list(DEFAULT_RULES if rules is None else rules)
        if overrides:
            seen = {rule.key for rule in chosen}
            chosen = [
                PatternRule(rule.key, rule.description, overrides[rule.key])
                if rule.key in overrides
                else rule
                for rule in chosen
            ]
            labels = {key: label for key, label, *_rest in PATTERN_FIELDS}
            for key, source in overrides.items():
                if key not in seen:
                    chosen.append(PatternRule(key, labels[key], source))
        object.__setattr__(self, "rules", tuple(chosen))
        object.__setattr__(self, "min_year", min_year)
        object.__setattr__(self, "max_year", max_year)
        object.__setattr__(self, "prec_clock", prec_clock)
        object.__setattr__(self, "prec_epoch", prec_epoch)
        object.__setattr__(self, "prec_date", prec_date)
        self.__post_init__()

    def __getattr__(self, name: str) -> str:
        for rule in self.rules:
            if rule.key == name:
                return rule.pattern
        raise AttributeError(name)

    def __post_init__(self) -> None:
        if self.min_year > self.max_year:
            raise ValueError("minimum year must not be after maximum year")
        for key, label, *_rest in LIMIT_FIELDS:
            if key in {"min_year", "max_year"}:
                continue
            if getattr(self, key) < 0:
                raise ValueError(f"{label} must be >= 0")

    def compile(self) -> CompiledTimestampPatterns:
        """Compile the rules, or raise ``ValueError`` when one is unusable."""

        compiled: list[CompiledRule] = []
        for rule in self.rules:
            label = rule.description.strip() or rule.key or "pattern"
            try:
                pattern = _compile_rule(rule.pattern)
            except ValueError as exc:
                raise ValueError(f"{label}: {exc}") from exc
            if pattern is None:
                continue
            try:
                kind = _kind_of(pattern)
            except ValueError as exc:
                raise ValueError(f"{label}: {exc}") from exc
            compiled.append(CompiledRule(kind, pattern))
        return CompiledTimestampPatterns(
            rules=tuple(compiled),
            min_year=self.min_year,
            max_year=self.max_year,
            prec_clock=self.prec_clock,
            prec_epoch=self.prec_epoch,
            prec_date=self.prec_date,
        )


@dataclass(frozen=True, slots=True)
class CompiledRule:
    """One expression compiled for a scan, and how its groups are read."""

    kind: str
    pattern: re.Pattern[str]


@dataclass(frozen=True, slots=True)
class CompiledTimestampPatterns:
    """Rules compiled once for a scan, plus the year window and priorities."""

    rules: tuple[CompiledRule, ...]
    min_year: int
    max_year: int
    prec_clock: int
    prec_epoch: int
    prec_date: int


def _compile_rule(source: str) -> re.Pattern[str] | None:
    if not source.strip():
        return None
    try:
        return re.compile(source)
    except re.error as exc:
        raise ValueError(f"invalid regular expression ({exc})") from exc


def _kind_of(pattern: re.Pattern[str]) -> str:
    groups = set(pattern.groupindex)
    for kind, required, optional in _KIND_SPECS:
        if required <= groups <= required | optional:
            return kind
    raise ValueError(
        "missing named groups for a clock (y, mo, d, h, mi, s), "
        "a day-month clock (a, b, y, h, mi), Unix milliseconds (ms), "
        "or a date (y, mo, d)"
    )



trace_module(sys.modules[__name__])
