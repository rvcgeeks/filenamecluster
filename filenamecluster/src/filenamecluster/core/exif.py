"""Read a capture time from a picture, video, or PDF. Nothing else is read.

Still images: JPEG, PNG, WebP, TIFF, and HEIF/AVIF, from the EXIF clock.
Videos: MP4, MOV, M4V, 3GP, and AVI. An embedded EXIF clock wins; otherwise
the container's creation time is used. PDFs use their CreationDate metadata.
Other files are left untouched.
No extra packages. Filesystem dates are never consulted.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

_MAX_READ = 1_048_576
_MAX_SEGMENT = 2_000_000
_JPEG_STANDALONE = {0x01, 0xD0, 0xD1, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7}
_HEIF_BRANDS = {b"heic", b"heix", b"heif", b"mif1", b"msf1", b"avif", b"avis"}
_VIDEO_BRANDS = {
    b"mp41",
    b"mp42",
    b"isom",
    b"iso2",
    b"iso4",
    b"iso5",
    b"iso6",
    b"M4V ",
    b"M4VH",
    b"M4VP",
    b"qt  ",
    b"3gp4",
    b"3gp5",
    b"3gp6",
    b"3gp7",
    b"3g2a",
    b"avc1",
    b"hvc1",
    b"hev1",
    b"F4V ",
    b"mmp4",
}
_MOVIE_BOXES = {b"moov", b"mdat", b"wide", b"free", b"skip"}
_MAC_EPOCH = datetime(1904, 1, 1, tzinfo=timezone.utc)
# DateTimeOriginal, DateTimeDigitized, then DateTime. The first one wins.
_WHEN_TAGS = (0x9003, 0x9004, 0x0132)
_EXIF_POINTER = 0x8769


def read_exif_timestamp(
    path: Path | str,
    min_year: int = 1990,
    max_year: int = 2100,
) -> datetime | None:
    """Return the capture time stored in ``path``, or ``None``.

    Pictures use the EXIF wall time ``YYYY:MM:DD HH:MM:SS``. Videos use an
    embedded EXIF clock when the file has one, otherwise the container's
    creation time. PDFs use ``CreationDate`` metadata. Other files are not
    read. A value outside ``min_year``..``max_year`` is ignored, the same
    window filenames use.
    """

    file = Path(path)
    try:
        if not file.is_file():
            return None
        with file.open("rb") as handle:
            header = handle.read(16)
            handle.seek(0)
            if _is_video(header):
                return _video_timestamp(handle, min_year, max_year)
            if header.startswith(b"%PDF-"):
                return _pdf_timestamp(handle, min_year, max_year)
            payload = _exif_payload(handle, header)
    except Exception:
        return None
    if not payload:
        return None
    try:
        return _datetime_from_tiff(payload, min_year, max_year)
    except Exception:
        return None


def _exif_payload(handle, header: bytes) -> bytes | None:
    if header.startswith(b"\xff\xd8"):
        return _jpeg_exif(handle)
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return _png_exif(handle)
    if len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return _webp_exif(handle)
    if _is_heif(header):
        return _search_exif_header(handle)
    if header[:2] in {b"II", b"MM"}:
        return handle.read(_MAX_READ)
    return None


def _is_heif(header: bytes) -> bool:
    return len(header) >= 12 and header[4:8] == b"ftyp" and header[8:12] in _HEIF_BRANDS


def _is_video(header: bytes) -> bool:
    if len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"AVI ":
        return True
    if len(header) >= 12 and header[4:8] == b"ftyp" and header[8:12] in _VIDEO_BRANDS:
        return True
    return len(header) >= 8 and header[4:8] in _MOVIE_BOXES


def _video_timestamp(handle, min_year: int, max_year: int) -> datetime | None:
    header = handle.read(12)
    handle.seek(0)
    if len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"AVI ":
        return _avi_timestamp(handle, min_year, max_year)
    return _bmff_timestamp(handle, min_year, max_year)


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
        if size < 0:
            return None
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


def _jpeg_marker(handle) -> int | None:
    if handle.read(1) != b"\xff":
        return None
    while True:
        value = handle.read(1)
        if not value:
            return None
        if value != b"\xff":
            return value[0]


def _jpeg_exif(handle) -> bytes | None:
    if handle.read(2) != b"\xff\xd8":
        return None
    while True:
        marker = _jpeg_marker(handle)
        if marker is None or marker in {0xD8, 0xD9, 0xDA}:
            return None
        if marker in _JPEG_STANDALONE:
            continue
        size_raw = handle.read(2)
        if len(size_raw) != 2:
            return None
        size = int.from_bytes(size_raw, "big")
        if size < 2:
            return None
        if size > _MAX_SEGMENT:
            handle.seek(size - 2, 1)
            continue
        payload = handle.read(size - 2)
        if len(payload) != size - 2:
            return None
        if marker == 0xE1 and payload.startswith(b"Exif\x00\x00"):
            return payload[6:]


def _png_exif(handle) -> bytes | None:
    if handle.read(8) != b"\x89PNG\r\n\x1a\n":
        return None
    while True:
        header = handle.read(8)
        if len(header) != 8:
            return None
        length = int.from_bytes(header[:4], "big")
        kind = header[4:8]
        if kind == b"IEND" or length > _MAX_SEGMENT:
            return None
        data = handle.read(length)
        handle.read(4)
        if len(data) != length:
            return None
        if kind == b"eXIf":
            return data


def _webp_exif(handle) -> bytes | None:
    header = handle.read(12)
    if len(header) != 12 or header[:4] != b"RIFF" or header[8:12] != b"WEBP":
        return None
    while True:
        chunk = handle.read(8)
        if len(chunk) != 8:
            return None
        kind = chunk[:4]
        size = int.from_bytes(chunk[4:8], "little")
        if size > _MAX_SEGMENT:
            return None
        data = handle.read(size)
        if len(data) != size:
            return None
        if size % 2:
            handle.read(1)
        if kind == b"EXIF":
            if data.startswith(b"Exif\x00\x00"):
                return data[6:]
            return data


def _search_exif_header(handle) -> bytes | None:
    """Find an ``Exif`` TIFF block inside a HEIF/AVIF file."""

    marker = b"Exif\x00\x00"
    pending = b""
    scanned = 0
    while scanned < _MAX_READ:
        block = handle.read(65536)
        if not block:
            return None
        scanned += len(block)
        data = pending + block
        found = data.find(marker)
        if found != -1:
            rest = data[found + len(marker) :]
            if len(rest) < 64:
                rest += handle.read(65536)
            return rest
        pending = data[1 - len(marker) :]
    return None


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
