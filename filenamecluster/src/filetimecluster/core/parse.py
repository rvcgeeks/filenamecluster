"""List a folder and pull a capture time out of each filename.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``. Introduction: ``readme.md``.

Subfolders and names with no usable timestamp are left for the caller to
skip. The clock in the filename is used, never the filesystem dates.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from filetimecluster.core.model_file import MODEL_NAME

# Higher wins when several stamps sit in one name. A camera-style
# YYYYMMDD_HHMMSS beats a trailing epoch (often an export id) and a bare date.
_CLOCK_GROUPS = frozenset({"y", "mo", "d", "h", "mi", "s"})
_PATTERN_GROUPS = {
    "clock_separated": _CLOCK_GROUPS,
    "clock_compact_sep": _CLOCK_GROUPS,
    "clock_compact_17": _CLOCK_GROUPS,
    "clock_compact_14": _CLOCK_GROUPS,
    "numeric_date": frozenset({"a", "b", "y", "h", "mi"}),
    "epoch_ms": frozenset({"ms"}),
    "date_only": frozenset({"y", "mo", "d"}),
}

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


@dataclass(frozen=True, slots=True)
class TimestampPatterns:
    """Filename patterns and the year window and priorities they are judged with.

    A blank pattern is turned off. The strings are the ones this tool ships
    with, so leaving the options alone recognises the same names as before.
    """

    clock_separated: str = (
        r"(?<!\d)(?P<y>\d{4})-(?P<mo>\d{2})-(?P<d>\d{2})-"
        r"(?P<h>\d{2})-(?P<mi>\d{2})-(?P<s>\d{2})(?:-(?P<ms>\d{3}))?"
    )
    clock_compact_sep: str = (
        r"(?<!\d)(?P<y>\d{4})(?P<mo>\d{2})(?P<d>\d{2})[_-]"
        r"(?P<h>\d{2})(?P<mi>\d{2})(?P<s>\d{2})(?P<ms>\d{1,3})?(?!\d)"
    )
    clock_compact_17: str = (
        r"(?<!\d)(?P<y>\d{4})(?P<mo>\d{2})(?P<d>\d{2})"
        r"(?P<h>\d{2})(?P<mi>\d{2})(?P<s>\d{2})(?P<ms>\d{3})(?!\d)"
    )
    clock_compact_14: str = (
        r"(?<!\d)(?P<y>\d{4})(?P<mo>\d{2})(?P<d>\d{2})"
        r"(?P<h>\d{2})(?P<mi>\d{2})(?P<s>\d{2})(?!\d)"
    )
    numeric_date: str = (
        r"(?<!\d)(?P<a>\d{1,2})-(?P<b>\d{1,2})-(?P<y>\d{4})\s+"
        r"(?P<h>\d{2})[.:](?P<mi>\d{2})(?:[.:](?P<s>\d{2}))?"
    )
    epoch_ms: str = r"(?<!\d)(?P<ms>\d{13})(?!\d)"
    date_only: str = r"(?<!\d)(?P<y>\d{4})[-_]?(?P<mo>\d{2})[-_]?(?P<d>\d{2})(?!\d)"
    min_year: int = 1990
    max_year: int = 2100
    prec_clock: int = 30
    prec_epoch: int = 20
    prec_date: int = 10

    def __post_init__(self) -> None:
        if self.min_year > self.max_year:
            raise ValueError("minimum year must not be after maximum year")
        for key, label, *_rest in LIMIT_FIELDS:
            if key in {"min_year", "max_year"}:
                continue
            if getattr(self, key) < 0:
                raise ValueError(f"{label} must be >= 0")

    def compile(self) -> CompiledTimestampPatterns:
        """Compile the patterns, or raise ``ValueError`` when one is unusable."""

        compiled: dict[str, re.Pattern[str] | None] = {}
        labels = {key: label for key, label, *_rest in PATTERN_FIELDS}
        for key, required in _PATTERN_GROUPS.items():
            try:
                compiled[key] = _compile_pattern(getattr(self, key), required)
            except ValueError as exc:
                raise ValueError(f"{labels[key]}: {exc}") from exc
        return CompiledTimestampPatterns(
            min_year=self.min_year,
            max_year=self.max_year,
            prec_clock=self.prec_clock,
            prec_epoch=self.prec_epoch,
            prec_date=self.prec_date,
            **compiled,
        )


@dataclass(frozen=True, slots=True)
class CompiledTimestampPatterns:
    """Patterns compiled once for a scan, plus the year window and priorities."""

    clock_separated: re.Pattern[str] | None
    clock_compact_sep: re.Pattern[str] | None
    clock_compact_17: re.Pattern[str] | None
    clock_compact_14: re.Pattern[str] | None
    numeric_date: re.Pattern[str] | None
    epoch_ms: re.Pattern[str] | None
    date_only: re.Pattern[str] | None
    min_year: int
    max_year: int
    prec_clock: int
    prec_epoch: int
    prec_date: int


def _compile_pattern(source: str, required: frozenset[str]) -> re.Pattern[str] | None:
    if not source.strip():
        return None
    try:
        pattern = re.compile(source)
    except re.error as exc:
        raise ValueError(f"invalid regular expression ({exc})") from exc
    missing = required - set(pattern.groupindex)
    if missing:
        names = ", ".join(sorted(missing))
        raise ValueError(f"missing named groups {names}")
    return pattern


_EVENT_FOLDER = re.compile(
    r"^\d+ \d{2}-\d{2}-\d{4} \d{2}\.\d{2}\.\d{2} to "
    r"(?:\d{2}-\d{2}-\d{4} )?\d{2}\.\d{2}\.\d{2}$"
)


def is_cluster_folder_name(name: str) -> bool:
    """True when ``name`` is a folder this tool would create for an event."""

    return bool(_EVENT_FOLDER.fullmatch(name))


@dataclass(frozen=True, slots=True)
class TimestampedFile:
    """A filename whose capture time could be read.

    ``source`` is the path relative to the chosen folder when the file already
    sits inside an event folder. It is empty for a file sitting directly in
    that folder. ``name`` stays the filename either way, so corrections keep
    matching after a file moves.
    """

    name: str
    timestamp: datetime
    source: str = ""


@dataclass(frozen=True, slots=True)
class FolderContents:
    """Names of the files and subfolders sitting directly in one folder, sorted.

    ``placed`` holds ``(event folder, filename)`` for photos already moved into
    an event folder. Other subfolders are listed and not entered.
    """

    files: tuple[str, ...]
    directories: tuple[str, ...]
    placed: tuple[tuple[str, str], ...] = ()


def scan_directory(directory: Path) -> FolderContents:
    """List the chosen folder, including photos already inside event folders.

    Other subfolders are recorded and not entered. The capture time still
    comes from each filename, not from filesystem dates.
    """

    folder = Path(directory)
    if not folder.is_dir():
        raise NotADirectoryError(folder)
    files: list[str] = []
    directories: list[str] = []
    placed: list[tuple[str, str]] = []
    for entry in sorted(folder.iterdir(), key=lambda item: item.name):
        if entry.is_dir():
            directories.append(entry.name)
            if is_cluster_folder_name(entry.name):
                placed.extend(_files_inside_event_folder(entry))
        elif entry.is_file() and entry.name != MODEL_NAME:
            files.append(entry.name)
    return FolderContents(tuple(files), tuple(directories), tuple(placed))


def _files_inside_event_folder(folder: Path) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for entry in sorted(folder.iterdir(), key=lambda item: item.name):
        if entry.is_file() and entry.name != MODEL_NAME:
            found.append((folder.name, entry.name))
    return found


def parse_timestamp(
    filename: str,
    patterns: TimestampPatterns | CompiledTimestampPatterns | None = None,
) -> datetime | None:
    """Return the capture time embedded in ``filename``, or ``None``.

    ``patterns`` defaults to :class:`TimestampPatterns`, which recognises
    ``IMG_YYYYMMDD_HHMMSS``, compact ``YYYYMMDDHHMMSS`` (with optional
    milliseconds), ``YYYY-MM-DD-HH-MM-SS``, ``DD-MM-YYYY HH.MM`` /
    ``MM-DD-YYYY HH.MM``, a bare ``YYYYMMDD``, and a 13-digit Unix millisecond
    stamp. Epoch values are converted to local time so they line up with
    camera names, which are local wall times.

    When a name contains more than one stamp, the one with the higher
    priority wins, and an earlier match wins a tie. With the defaults a clock
    beats a trailing epoch, and a clock beats a date that has no time. A bare
    date is taken as local midnight.
    """

    if isinstance(patterns, CompiledTimestampPatterns):
        compiled = patterns
    else:
        compiled = (patterns or TimestampPatterns()).compile()
    return _timestamp_from(Path(filename).name, compiled)


def _timestamp_from(name: str, patterns: CompiledTimestampPatterns) -> datetime | None:
    found: list[tuple[int, int, datetime]] = []
    found.extend(_clock_matches(name, patterns))
    found.extend(_numeric_date_matches(name, patterns))
    found.extend(_epoch_matches(name, patterns))
    found.extend(_date_only_matches(name, patterns))
    if not found:
        return None
    found.sort(key=lambda item: (-item[0], item[1]))
    return found[0][2]


def _clock_matches(
    name: str, patterns: CompiledTimestampPatterns
) -> list[tuple[int, int, datetime]]:
    found: list[tuple[int, int, datetime]] = []
    for pattern in (
        patterns.clock_separated,
        patterns.clock_compact_sep,
        patterns.clock_compact_17,
        patterns.clock_compact_14,
    ):
        if pattern is None:
            continue
        for match in pattern.finditer(name):
            millis = _millis_to_microseconds(match.groupdict().get("ms"))
            if millis is None:
                continue
            stamp = _make_datetime(
                int(match.group("y")),
                int(match.group("mo")),
                int(match.group("d")),
                int(match.group("h")),
                int(match.group("mi")),
                int(match.group("s")),
                millis,
                patterns.min_year,
                patterns.max_year,
            )
            if stamp is not None:
                found.append((patterns.prec_clock, match.start(), stamp))
    return found


def _numeric_date_matches(
    name: str, patterns: CompiledTimestampPatterns
) -> list[tuple[int, int, datetime]]:
    if patterns.numeric_date is None:
        return []
    found: list[tuple[int, int, datetime]] = []
    for match in patterns.numeric_date.finditer(name):
        year = int(match.group("y"))
        first = int(match.group("a"))
        second = int(match.group("b"))
        hour = int(match.group("h"))
        minute = int(match.group("mi"))
        second_value = int(match.groupdict().get("s") or 0)
        # Day-month-year matches this collection's dates. Month-day-year is
        # accepted only when day-month-year is impossible (month > 12).
        day_month = _make_datetime(
            year, second, first, hour, minute, second_value, 0, patterns.min_year, patterns.max_year
        )
        month_day = _make_datetime(
            year, first, second, hour, minute, second_value, 0, patterns.min_year, patterns.max_year
        )
        stamp = day_month or month_day
        if stamp is not None:
            found.append((patterns.prec_clock, match.start(), stamp))
    return found


def _epoch_matches(
    name: str, patterns: CompiledTimestampPatterns
) -> list[tuple[int, int, datetime]]:
    if patterns.epoch_ms is None:
        return []
    found: list[tuple[int, int, datetime]] = []
    for match in patterns.epoch_ms.finditer(name):
        stamp = _from_epoch_millis(int(match.group("ms")), patterns.min_year, patterns.max_year)
        if stamp is not None:
            found.append((patterns.prec_epoch, match.start(), stamp))
    return found


def _date_only_matches(
    name: str, patterns: CompiledTimestampPatterns
) -> list[tuple[int, int, datetime]]:
    if patterns.date_only is None:
        return []
    found: list[tuple[int, int, datetime]] = []
    for match in patterns.date_only.finditer(name):
        stamp = _make_datetime(
            int(match.group("y")),
            int(match.group("mo")),
            int(match.group("d")),
            min_year=patterns.min_year,
            max_year=patterns.max_year,
        )
        if stamp is not None:
            found.append((patterns.prec_date, match.start(), stamp))
    return found


def _millis_to_microseconds(text: str | None) -> int | None:
    if not text:
        return 0
    scale = {1: 100_000, 2: 10_000, 3: 1_000}.get(len(text))
    if scale is None:
        return None
    return int(text) * scale


def _make_datetime(
    year: int,
    month: int,
    day: int,
    hour: int = 0,
    minute: int = 0,
    second: int = 0,
    microsecond: int = 0,
    min_year: int = 1990,
    max_year: int = 2100,
) -> datetime | None:
    if not min_year <= year <= max_year:
        return None
    try:
        return datetime(year, month, day, hour, minute, second, microsecond)
    except ValueError:
        return None


def _from_epoch_millis(millis: int, min_year: int, max_year: int) -> datetime | None:
    try:
        stamp = datetime.fromtimestamp(millis / 1000.0)
    except (OverflowError, OSError, ValueError):
        return None
    if not min_year <= stamp.year <= max_year:
        return None
    return stamp
