"""Capture times stored inside pictures, videos, and PDFs.

``filenamecluster.core`` re-exports ``read_exif_timestamp``. Other packages
import it from there.
"""

from .image import (
    _MAX_READ,
    _MAX_SEGMENT,
    _jpeg_exif,
    _jpeg_marker,
    _png_exif,
    _search_exif_header,
    _webp_exif,
)
from .pdf import _parse_pdf_date, _pdf_date_after, _pdf_timestamp
from .read import read_exif_timestamp
from .tiff import _ascii_at, _datetime_from_tiff, _parse_clock, _u16, _u32, _walk_ifd
from .video import (
    _avi_timestamp,
    _bmff_timestamp,
    _box_header,
    _mvhd_in,
    _mvhd_time,
    _parse_idit,
    _time_in_block,
)

__all__ = [
    "_MAX_READ",
    "_MAX_SEGMENT",
    "_ascii_at",
    "_avi_timestamp",
    "_bmff_timestamp",
    "_box_header",
    "_datetime_from_tiff",
    "_jpeg_exif",
    "_jpeg_marker",
    "_mvhd_in",
    "_mvhd_time",
    "_parse_clock",
    "_parse_idit",
    "_parse_pdf_date",
    "_pdf_date_after",
    "_pdf_timestamp",
    "_png_exif",
    "_search_exif_header",
    "_time_in_block",
    "_u16",
    "_u32",
    "_walk_ifd",
    "_webp_exif",
    "read_exif_timestamp",
]
