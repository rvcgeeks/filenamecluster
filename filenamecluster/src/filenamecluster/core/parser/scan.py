"""List a folder and pull a capture time out of each filename.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``. Introduction: ``readme.md``.

Subfolders and names with no usable timestamp are left for the caller to
skip. The clock in the filename is used, never the filesystem dates.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from filenamecluster.core.progress import expect, tick
from filenamecluster.log import detail, trace_module
from .folders import is_cluster_folder_name
from .patterns import CompiledTimestampPatterns, TimestampPatterns

MODEL_NAME = "filenamecluster-model.json"


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
    origin: str = ""


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

    Other subfolders are recorded and not entered. Filesystem dates are not used.
    """

    folder = Path(directory)
    if not folder.is_dir():
        raise NotADirectoryError(folder)
    files: list[str] = []
    directories: list[str] = []
    placed: list[tuple[str, str]] = []
    entries = sorted(folder.iterdir(), key=lambda item: item.name)
    expect(len(entries))
    for entry in entries:
        tick()
        if entry.is_dir():
            directories.append(entry.name)
            if is_cluster_folder_name(entry.name):
                placed.extend(_files_inside_event_folder(entry))
        elif entry.is_file() and entry.name != MODEL_NAME:
            files.append(entry.name)
    detail(
        "directory_scanned",
        path=str(folder),
        files=len(files),
        directories=len(directories),
        placed=len(placed),
        other_directories=[name for name in directories if not is_cluster_folder_name(name)],
    )
    return FolderContents(tuple(files), tuple(directories), tuple(placed))


def _same_directory(left: Path, right: Path) -> bool:
    try:
        return left.resolve() == right.resolve()
    except OSError:
        return left == right


def _fingerprint_row(rows: list[tuple], origin: str, relative: str, path: Path) -> None:
    try:
        info = path.stat()
    except OSError:
        return
    rows.append((origin, relative, info.st_size, info.st_mtime_ns))


def fingerprint_listing(directory: Path, origin: str = "") -> tuple[FolderContents, tuple]:
    """List ``directory`` once and record each file's size and modification time."""

    root = Path(directory)
    contents = scan_directory(root)
    rows: list[tuple] = []
    for name in contents.files:
        _fingerprint_row(rows, origin, name, root / name)
    for dirname, name in contents.placed:
        _fingerprint_row(rows, origin, f"{dirname}/{name}", root / dirname / name)
    return contents, tuple(rows)


def folder_fingerprint(directory: Path | str, source: Path | str | None = None) -> tuple:
    """Identity of the files a preview would read. The model file is not included."""

    storage = Path(directory)
    incoming = storage if source is None else Path(source)
    _contents, rows = fingerprint_listing(storage, "")
    collected = list(rows)
    if not _same_directory(storage, incoming):
        _incoming, extra = fingerprint_listing(incoming, "input")
        collected.extend(extra)
    return tuple(sorted(collected))


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

    ``patterns`` defaults to :class:`TimestampPatterns`. Its built-in rules
    recognise ``IMG_YYYYMMDD_HHMMSS``, compact ``YYYYMMDDHHMMSS`` (with
    optional milliseconds), ``YYYY-MM-DD-HH-MM-SS``, ``DD-MM-YYYY HH.MM`` /
    ``MM-DD-YYYY HH.MM``, a bare ``YYYYMMDD``, and a 13-digit Unix millisecond
    stamp. Extra rules in ``patterns.rules`` are read the same way. Epoch
    values are converted to local time so they line up with camera names,
    which are local wall times.

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
    for rule in patterns.rules:
        if rule.kind == "clock":
            found.extend(_clock_matches(name, rule.pattern, patterns))
        elif rule.kind == "numeric_date":
            found.extend(_numeric_date_matches(name, rule.pattern, patterns))
        elif rule.kind == "epoch_ms":
            found.extend(_epoch_matches(name, rule.pattern, patterns))
        elif rule.kind == "date_only":
            found.extend(_date_only_matches(name, rule.pattern, patterns))
    if not found:
        detail("timestamp_missing", name=name, rules=len(patterns.rules))
        return None
    found.sort(key=lambda item: (-item[0], item[1]))
    priority, start, stamp = found[0]
    detail(
        "timestamp_chosen",
        name=name,
        candidates=len(found),
        priority=priority,
        start=start,
        stamp=stamp.isoformat(sep=" "),
    )
    return stamp


def _clock_matches(
    name: str, pattern: re.Pattern[str], patterns: CompiledTimestampPatterns
) -> list[tuple[int, int, datetime]]:
    found: list[tuple[int, int, datetime]] = []
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
    name: str, pattern: re.Pattern[str], patterns: CompiledTimestampPatterns
) -> list[tuple[int, int, datetime]]:
    found: list[tuple[int, int, datetime]] = []
    for match in pattern.finditer(name):
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
    name: str, pattern: re.Pattern[str], patterns: CompiledTimestampPatterns
) -> list[tuple[int, int, datetime]]:
    found: list[tuple[int, int, datetime]] = []
    for match in pattern.finditer(name):
        stamp = _from_epoch_millis(int(match.group("ms")), patterns.min_year, patterns.max_year)
        if stamp is not None:
            found.append((patterns.prec_epoch, match.start(), stamp))
    return found


def _date_only_matches(
    name: str, pattern: re.Pattern[str], patterns: CompiledTimestampPatterns
) -> list[tuple[int, int, datetime]]:
    found: list[tuple[int, int, datetime]] = []
    for match in pattern.finditer(name):
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
        detail("millis_rejected", digits=len(text))
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
        detail("timestamp_rejected", year=year, month=month, day=day, reason="year")
        return None
    try:
        return datetime(year, month, day, hour, minute, second, microsecond)
    except ValueError:
        detail(
            "timestamp_rejected",
            year=year,
            month=month,
            day=day,
            hour=hour,
            minute=minute,
            second=second,
            reason="invalid",
        )
        return None


def _from_epoch_millis(millis: int, min_year: int, max_year: int) -> datetime | None:
    try:
        stamp = datetime.fromtimestamp(millis / 1000.0)
    except (OverflowError, OSError, ValueError):
        detail("epoch_rejected", millis=millis, reason="overflow")
        return None
    if not min_year <= stamp.year <= max_year:
        detail("epoch_rejected", millis=millis, year=stamp.year, reason="year")
        return None
    return stamp



trace_module(sys.modules[__name__])
