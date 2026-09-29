"""A TIFF block's DateTimeOriginal is the capture clock."""

import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from filenamecluster.core.exif import read_exif_timestamp

WHEN = "2024:06:01 12:30:45"
OLDER = "2010:01:01 08:00:00"


def _u16(value: int, order: str) -> bytes:
    return value.to_bytes(2, order)


def _u32(value: int, order: str) -> bytes:
    return value.to_bytes(4, order)


def _tiff(newer: str, older: str | None = None, *, endian: str = "little") -> bytes:
    """TIFF whose Exif block prefers DateTimeOriginal over DateTime."""

    order = endian
    bom = b"II" if order == "little" else b"MM"
    newer_bytes = newer.encode("ascii") + b"\x00"
    older_bytes = (older or newer).encode("ascii") + b"\x00"
    ifd0 = 8
    exif_at = ifd0 + 2 + 24 + 4
    strings = exif_at + 2 + 12 + 4
    newer_at = strings + len(older_bytes)
    blob = bytearray()
    blob += bom + _u16(42, order) + _u32(ifd0, order)
    blob += _u16(2, order)
    blob += _u16(0x0132, order) + _u16(2, order) + _u32(len(older_bytes), order) + _u32(strings, order)
    blob += _u16(0x8769, order) + _u16(4, order) + _u32(1, order) + _u32(exif_at, order)
    blob += _u32(0, order)
    blob += _u16(1, order)
    blob += _u16(0x9003, order) + _u16(2, order) + _u32(len(newer_bytes), order) + _u32(newer_at, order)
    blob += _u32(0, order)
    blob += older_bytes + newer_bytes
    return bytes(blob)


class TiffClockTests(unittest.TestCase):
    def test_big_endian_tiff_prefers_the_original_clock(self):
        expected = datetime(2024, 6, 1, 12, 30, 45)
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "photo.tif"
            path.write_bytes(_tiff(WHEN, OLDER, endian="big"))
            self.assertEqual(read_exif_timestamp(path), expected)
