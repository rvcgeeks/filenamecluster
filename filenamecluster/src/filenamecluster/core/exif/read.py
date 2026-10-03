"""Choose how to read a capture time from a picture, video, or PDF.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).

Still images use the EXIF clock. Videos use an embedded EXIF clock when the
file has one, otherwise the container's creation time. PDFs use CreationDate.
Other files are left untouched. Filesystem dates are never consulted.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from filenamecluster.log import detail, trace_module
from .image import _MAX_READ, _jpeg_exif, _png_exif, _search_exif_header, _webp_exif
from .pdf import _pdf_timestamp
from .tiff import _datetime_from_tiff
from .video import _video_timestamp

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


_CLOCK_CACHE: dict[tuple, datetime | None] = {}


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
        info = file.stat()
    except OSError:
        detail("metadata_skipped", path=str(file), reason="not_a_file")
        return None
    if not file.is_file():
        detail("metadata_skipped", path=str(file), reason="not_a_file")
        return None
    try:
        key = (str(file.resolve()), info.st_size, info.st_mtime_ns, min_year, max_year)
    except OSError:
        key = None
    if key is not None and key in _CLOCK_CACHE:
        return _CLOCK_CACHE[key]

    def finish(stamp: datetime | None) -> datetime | None:
        if key is not None:
            _CLOCK_CACHE[key] = stamp
        return stamp

    try:
        with file.open("rb") as handle:
            header = handle.read(16)
            handle.seek(0)
            if _is_video(header):
                stamp = _video_timestamp(handle, min_year, max_year)
                detail(
                    "metadata_clock",
                    path=file.name,
                    kind="video",
                    found=stamp is not None,
                    stamp=None if stamp is None else stamp.isoformat(sep=" "),
                )
                return finish(stamp)
            if header.startswith(b"%PDF-"):
                stamp = _pdf_timestamp(handle, min_year, max_year)
                detail(
                    "metadata_clock",
                    path=file.name,
                    kind="pdf",
                    found=stamp is not None,
                    stamp=None if stamp is None else stamp.isoformat(sep=" "),
                )
                return finish(stamp)
            payload = _exif_payload(handle, header)
    except Exception:  # noqa: BLE001  # a damaged container must not stop the scan
        detail("metadata_skipped", path=file.name, reason="unreadable")
        return finish(None)
    if not payload:
        detail("metadata_skipped", path=file.name, reason="no_exif")
        return finish(None)
    try:
        stamp = _datetime_from_tiff(payload, min_year, max_year)
    except Exception:  # noqa: BLE001  # a damaged container must not stop the scan
        detail("metadata_skipped", path=file.name, reason="bad_exif")
        return finish(None)
    detail(
        "metadata_clock",
        path=file.name,
        kind="exif",
        found=stamp is not None,
        stamp=None if stamp is None else stamp.isoformat(sep=" "),
    )
    return finish(stamp)


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



trace_module(sys.modules[__name__])
