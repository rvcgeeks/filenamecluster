"""Read a PDF CreationDate. The document contents are not read.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
"""

from __future__ import annotations

import re
import sys
from datetime import datetime, timedelta, timezone

from filenamecluster.log import trace_module
from .image import _MAX_READ


def _pdf_timestamp(handle, min_year: int, max_year: int) -> datetime | None:
    """Read PDF CreationDate or XMP CreateDate from bounded head/tail data."""

    handle.seek(0, 2)
    size = handle.tell()
    handle.seek(0)
    chunks = [handle.read(_MAX_READ)]
    if size > _MAX_READ:
        handle.seek(max(0, size - _MAX_READ))
        chunks.append(handle.read(_MAX_READ))
    data = b"\n".join(chunks)

    for marker in (b"/CreationDate", b"xmp:CreateDate"):
        start = 0
        while True:
            index = data.find(marker, start)
            if index < 0:
                break
            text = _pdf_date_after(data, index + len(marker))
            if text:
                stamp = _parse_pdf_date(text, min_year, max_year)
                if stamp is not None:
                    return stamp
            start = index + len(marker)
    return None


def _pdf_date_after(data: bytes, offset: int) -> str:
    """Return the short string value following a PDF or XMP date key."""

    limit = min(len(data), offset + 256)
    cursor = offset
    while cursor < limit and data[cursor] in b" \t\r\n=":
        cursor += 1
    quote = data[cursor : cursor + 1]
    if quote == b"(":
        cursor += 1
        raw = bytearray()
        escaped = False
        while cursor < limit and len(raw) < 128:
            value = data[cursor]
            cursor += 1
            if escaped:
                raw.append(value)
                escaped = False
            elif value == 0x5C:
                escaped = True
            elif value == 0x29:
                break
            else:
                raw.append(value)
        return raw.decode("ascii", "ignore").strip()
    if quote in {b'"', b"'"}:
        end = data.find(quote, cursor + 1, limit)
        if end >= 0:
            return data[cursor + 1 : end].decode("ascii", "ignore").strip()
    if quote == b">":
        end = data.find(b"<", cursor + 1, limit)
        if end >= 0:
            return data[cursor + 1 : end].decode("ascii", "ignore").strip()
    return ""


_PDF_DATE = re.compile(
    r"^(?:D:)?(?P<y>\d{4})(?P<mo>\d{2})(?P<d>\d{2})"
    r"(?P<h>\d{2})?(?P<mi>\d{2})?(?P<s>\d{2})?"
    r"(?:(?P<zone>Z|[+-])(?P<zh>\d{2})?'?(?P<zm>\d{2})?'?)?"
)


def _parse_pdf_date(text: str, min_year: int, max_year: int) -> datetime | None:
    if "-" in text[:10]:
        try:
            stamp = datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        match = _PDF_DATE.match(text.strip())
        if match is None:
            return None
        values = match.groupdict()
        try:
            stamp = datetime(
                int(values["y"]),
                int(values["mo"]),
                int(values["d"]),
                int(values["h"] or 0),
                int(values["mi"] or 0),
                int(values["s"] or 0),
            )
            zone = values["zone"]
            if zone:
                if zone == "Z":
                    offset = timedelta()
                else:
                    minutes = int(values["zh"] or 0) * 60 + int(values["zm"] or 0)
                    offset = timedelta(minutes=minutes if zone == "+" else -minutes)
                stamp = stamp.replace(tzinfo=timezone(offset))
        except (OverflowError, ValueError):
            return None
    if stamp.tzinfo is not None:
        try:
            stamp = stamp.astimezone().replace(tzinfo=None)
        except (OverflowError, OSError, ValueError):
            return None
    if not min_year <= stamp.year <= max_year:
        return None
    return stamp


trace_module(sys.modules[__name__])
