"""Read a capture clock from an EXIF TIFF block.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
"""

from __future__ import annotations

import sys
from datetime import datetime

from filenamecluster.log import trace_module

_WHEN_TAGS = (0x9003, 0x9004, 0x0132)
_EXIF_POINTER = 0x8769


def _datetime_from_tiff(data: bytes, min_year: int, max_year: int) -> datetime | None:
    if len(data) < 8 or data[:2] not in {b"II", b"MM"}:
        return None
    order = "little" if data[:2] == b"II" else "big"
    if _u16(data, 2, order) != 42:
        return None
    found: dict[int, str] = {}
    _walk_ifd(data, _u32(data, 4, order), order, found, set(), 0)
    for tag in _WHEN_TAGS:
        text = found.get(tag)
        if text:
            stamp = _parse_clock(text, min_year, max_year)
            if stamp is not None:
                return stamp
    return None


def _walk_ifd(
    data: bytes,
    offset: int | None,
    order: str,
    found: dict[int, str],
    seen: set[int],
    depth: int,
) -> None:
    if offset is None or depth > 4 or offset in seen or offset < 0 or offset + 2 > len(data):
        return
    seen.add(offset)
    count = _u16(data, offset, order)
    if count is None or count > 512:
        return
    entry = offset + 2
    nested: int | None = None
    for _ in range(count):
        if entry + 12 > len(data):
            return
        tag = _u16(data, entry, order)
        kind = _u16(data, entry + 2, order)
        number = _u32(data, entry + 4, order)
        if tag == _EXIF_POINTER and kind == 4 and number == 1:
            nested = _u32(data, entry + 8, order)
        elif tag in _WHEN_TAGS and kind == 2 and number and tag not in found:
            text = _ascii_at(data, entry, number, order)
            if text:
                found[tag] = text
        entry += 12
    if nested is not None:
        _walk_ifd(data, nested, order, found, seen, depth + 1)


def _ascii_at(data: bytes, entry: int, count: int, order: str) -> str:
    if count <= 4:
        raw = data[entry + 8 : entry + 8 + count]
    else:
        offset = _u32(data, entry + 8, order)
        if offset is None or offset < 0 or offset + count > len(data):
            return ""
        raw = data[offset : offset + count]
    return raw.split(b"\x00", 1)[0].decode("ascii", "ignore").strip()


def _parse_clock(text: str, min_year: int, max_year: int) -> datetime | None:
    if len(text) < 19:
        return None
    try:
        stamp = datetime.strptime(text[:19], "%Y:%m:%d %H:%M:%S")
    except ValueError:
        return None
    if not min_year <= stamp.year <= max_year:
        return None
    return stamp


def _u16(data: bytes, offset: int, order: str) -> int | None:
    if offset < 0 or offset + 2 > len(data):
        return None
    return int.from_bytes(data[offset : offset + 2], order)


def _u32(data: bytes, offset: int, order: str) -> int | None:
    if offset < 0 or offset + 4 > len(data):
        return None
    return int.from_bytes(data[offset : offset + 4], order)


trace_module(sys.modules[__name__])
