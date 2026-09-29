"""Which files get a metadata clock, and which are left alone."""

import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from filenamecluster.core.exif import read_exif_timestamp
from filenamecluster.core.operations.pipeline import cluster_directory

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


def _jpeg(tiff: bytes, *, tem: bool = False, bulky: bool = False) -> bytes:
    payload = b"Exif\x00\x00" + tiff
    app1 = b"\xff\xe1" + (len(payload) + 2).to_bytes(2, "big") + payload
    body = b""
    if bulky:
        pad = b"\x00" * 40
        body += b"\xff\xe0" + (len(pad) + 2).to_bytes(2, "big") + pad
    if tem:
        body += b"\xff\x01"
    return b"\xff\xd8" + body + app1 + b"\xff\xd9"


class ReadTimestampTests(unittest.TestCase):
    def test_unusable_files_have_no_timestamp(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "notes.txt").write_bytes(b"hello")
            (root / "empty.jpg").write_bytes(b"")
            (root / "cut.jpg").write_bytes(b"\xff\xd8\xff\xe1\x00")
            (root / "bad.jpg").write_bytes(_jpeg(_tiff("not-a-date-but-long!!")))
            (root / "old.jpg").write_bytes(_jpeg(_tiff("1980:01:01 00:00:00")))
            (root / "loop.tif").write_bytes(b"II" + (42).to_bytes(2, "little") + (8).to_bytes(4, "little") + (1).to_bytes(2, "little") + (0x8769).to_bytes(2, "little") + (4).to_bytes(2, "little") + (1).to_bytes(4, "little") + (8).to_bytes(4, "little") + (0).to_bytes(4, "little"))
            (root / "plain.png").write_bytes(b"\x89PNG\r\n\x1a\n" + (0).to_bytes(4, "big") + b"IEND" + b"\x00\x00\x00\x00")
            for name in ("notes.txt", "empty.jpg", "cut.jpg", "bad.jpg", "old.jpg", "loop.tif", "plain.png"):
                self.assertIsNone(read_exif_timestamp(root / name), name)
            self.assertIsNone(read_exif_timestamp(root))

    def test_filename_wins_and_exif_fills_the_gap(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "IMG_20240101_101500.jpg").write_bytes(_jpeg(_tiff("2011:02:02 03:04:05")))
            (root / "plain.jpg").write_bytes(_jpeg(_tiff(WHEN)))
            (root / "notes.txt").write_bytes(b"x")
            result = cluster_directory(root)
            found = {item.name: item.timestamp for cluster in result.clusters for item in cluster.files}
            self.assertEqual(found["IMG_20240101_101500.jpg"], datetime(2024, 1, 1, 10, 15, 0))
            self.assertEqual(found["plain.jpg"], datetime(2024, 6, 1, 12, 30, 45))
            self.assertEqual(result.ignored_without_timestamp, ("notes.txt",))
