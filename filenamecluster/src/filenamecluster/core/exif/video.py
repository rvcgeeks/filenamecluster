"""Read a capture time from an MP4, MOV, M4V, 3GP, or AVI container.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
An embedded EXIF clock wins. Otherwise the container's creation time is used.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone

from filenamecluster.log import trace_module
from .image import _MAX_READ
from .tiff import _datetime_from_tiff

_MAC_EPOCH = datetime(1904, 1, 1, tzinfo=timezone.utc)


def _video_timestamp(handle, min_year: int, max_year: int) -> datetime | None:
    header = handle.read(12)
    handle.seek(0)
    if len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"AVI ":
        return _avi_timestamp(handle, min_year, max_year)
    return _bmff_timestamp(handle, min_year, max_year)


def _bmff_timestamp(handle, min_year: int, max_year: int) -> datetime | None:
    """EXIF inside ``moov`` wins. Otherwise the movie header's creation time."""

    exif_stamp = None
    created = None
    while True:
        box = _box_header(handle)
        if box is None:
            break
        kind, start, size, header_len = box
        payload = size - header_len
        if kind == b"moov" and 0 <= payload <= _MAX_READ:
            data = handle.read(payload)
            if len(data) != payload:
                break
            exif_stamp = _embedded_exif_time(data, min_year, max_year)
            created = _mvhd_in(data, min_year, max_year)
            break
        handle.seek(start + size)
    if exif_stamp is not None:
        return exif_stamp
    return created


def _box_header(handle) -> tuple[bytes, int, int, int] | None:
    start = handle.tell()
    raw = handle.read(8)
    if len(raw) < 8:
        return None
    size = int.from_bytes(raw[:4], "big")
    kind = raw[4:8]
    header_len = 8
    if size == 1:
        large = handle.read(8)
        if len(large) < 8:
            return None
        size = int.from_bytes(large, "big")
        header_len = 16
    elif size == 0:
        handle.seek(0, 2)
        size = handle.tell() - start
        handle.seek(start + header_len)
    if size < header_len:
        return None
    return kind, start, size, header_len


def _mvhd_in(data: bytes, min_year: int, max_year: int) -> datetime | None:
    offset = 0
    while offset + 8 <= len(data):
        size = int.from_bytes(data[offset : offset + 4], "big")
        kind = data[offset + 4 : offset + 8]
        header_len = 8
        if size == 1 and offset + 16 <= len(data):
            size = int.from_bytes(data[offset + 8 : offset + 16], "big")
            header_len = 16
        if size < header_len or offset + size > len(data):
            return None
        if kind == b"mvhd":
            return _mvhd_time(data[offset + header_len : offset + size], min_year, max_year)
        offset += size
    return None


def _mvhd_time(body: bytes, min_year: int, max_year: int) -> datetime | None:
    if not body:
        return None
    if body[0] == 0 and len(body) >= 8:
        seconds = int.from_bytes(body[4:8], "big")
    elif body[0] == 1 and len(body) >= 12:
        seconds = int.from_bytes(body[4:12], "big")
    else:
        return None
    if seconds <= 0:
        return None
    try:
        utc = _MAC_EPOCH + timedelta(seconds=seconds)
        local = utc.astimezone().replace(tzinfo=None)
    except (OverflowError, OSError, ValueError):
        return None
    if not min_year <= local.year <= max_year:
        return None
    return local


def _avi_timestamp(handle, min_year: int, max_year: int) -> datetime | None:
    handle.seek(0, 2)
    file_end = handle.tell()
    handle.seek(12)
    while handle.tell() + 8 <= file_end:
        raw = handle.read(8)
        if len(raw) < 8:
            return None
        kind = raw[:4]
        size = int.from_bytes(raw[4:8], "little")
        if kind == b"LIST" and size >= 4:
            list_type = handle.read(4)
            inner = size - 4
            if list_type == b"hdrl" and inner <= _MAX_READ:
                data = handle.read(inner)
                return _time_in_block(data, min_year, max_year)
            handle.seek(max(inner, 0), 1)
        elif kind == b"IDIT" and size <= 128:
            stamp = _parse_idit(handle.read(size), min_year, max_year)
            if stamp is not None:
                return stamp
        else:
            handle.seek(size, 1)
        if size & 1:
            handle.seek(1, 1)
    return None


def _time_in_block(data: bytes, min_year: int, max_year: int) -> datetime | None:
    exif_stamp = _embedded_exif_time(data, min_year, max_year)
    if exif_stamp is not None:
        return exif_stamp
    offset = 0
    while offset + 8 <= len(data):
        kind = data[offset : offset + 4]
        size = int.from_bytes(data[offset + 4 : offset + 8], "little")
        start = offset + 8
        if size < 0 or start + size > len(data):
            return None
        body = data[start : start + size]
        if kind == b"IDIT":
            stamp = _parse_idit(body, min_year, max_year)
            if stamp is not None:
                return stamp
        if kind == b"LIST" and size >= 4:
            stamp = _time_in_block(body[4:], min_year, max_year)
            if stamp is not None:
                return stamp
        offset = start + size + (size & 1)
    return None


def _parse_idit(body: bytes, min_year: int, max_year: int) -> datetime | None:
    text = body.split(b"\x00", 1)[0].decode("ascii", "ignore").strip()
    try:
        stamp = datetime.strptime(text, "%a %b %d %H:%M:%S %Y")
    except ValueError:
        return None
    if not min_year <= stamp.year <= max_year:
        return None
    return stamp


def _embedded_exif_time(data: bytes, min_year: int, max_year: int) -> datetime | None:
    marker = b"Exif\x00\x00"
    index = data.find(marker)
    if index == -1:
        return None
    return _datetime_from_tiff(data[index + len(marker) :], min_year, max_year)


trace_module(sys.modules[__name__])
