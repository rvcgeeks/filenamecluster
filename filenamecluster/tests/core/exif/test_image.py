"""EXIF blocks pulled out of JPEG, PNG, WebP, and HEIF."""

import unittest
import zlib
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from filenamecluster.core import read_exif_timestamp

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


def _png(tiff: bytes) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            len(data).to_bytes(4, "big")
            + kind
            + data
            + (zlib.crc32(kind + data) & 0xFFFFFFFF).to_bytes(4, "big")
        )

    return b"\x89PNG\r\n\x1a\n" + chunk(b"eXIf", tiff) + chunk(b"IEND", b"")


def _webp(tiff: bytes) -> bytes:
    data = b"Exif\x00\x00" + tiff
    if len(data) % 2 == 0:
        data += b"\x00"
    chunk = b"EXIF" + len(data).to_bytes(4, "little") + data + b"\x00"
    body = b"WEBP" + chunk
    return b"RIFF" + len(body).to_bytes(4, "little") + body


def _heif(tiff: bytes, *, gap: int = 0) -> bytes:
    payload = b"ftyp" + b"heic" + b"\x00\x00\x00\x00" + b"heic"
    box = (len(payload) + 4).to_bytes(4, "big") + payload
    return box + (b"\x00" * gap) + b"Exif\x00\x00" + tiff


class ExifTimestampTests(unittest.TestCase):
    def test_jpeg_png_webp_and_heif(self):
        expected = datetime(2024, 6, 1, 12, 30, 45)
        blobs = {
            "a.jpg": _jpeg(_tiff(WHEN, OLDER), tem=True),
            "b.png": _png(_tiff(WHEN, OLDER)),
            "c.webp": _webp(_tiff(WHEN, OLDER)),
            "e.heic": _heif(_tiff(WHEN, OLDER)),
        }
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, blob in blobs.items():
                (root / name).write_bytes(blob)
                self.assertEqual(read_exif_timestamp(root / name), expected, name)

    def test_heif_marker_is_found_past_the_first_read(self):
        blob = _heif(_tiff(WHEN), gap=70_000)
        head = _heif(b"")[: _heif(b"").index(b"Exif")]
        tail = b"\x00" * (65530 - len(head)) + b"Exif\x00\x00" + _tiff(WHEN)
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "late.heic").write_bytes(blob)
            (root / "split.heic").write_bytes(head + tail)
            expected = datetime(2024, 6, 1, 12, 30, 45)
            self.assertEqual(read_exif_timestamp(root / "late.heic"), expected)
            self.assertEqual(read_exif_timestamp(root / "split.heic"), expected)

    def test_a_bulky_segment_before_exif_is_skipped(self):
        tiff = _tiff(WHEN)
        app1 = len(b"Exif\x00\x00" + tiff) + 2
        pad = b"\x00" * (app1 + 100)
        jpeg = b"\xff\xd8"
        jpeg += b"\xff\xe0" + (len(pad) + 2).to_bytes(2, "big") + pad
        payload = b"Exif\x00\x00" + tiff
        jpeg += b"\xff\xe1" + (len(payload) + 2).to_bytes(2, "big") + payload + b"\xff\xd9"
        with (
            patch("filenamecluster.core.exif.image._MAX_SEGMENT", app1 + 10),
            TemporaryDirectory() as tmp,
        ):
            path = Path(tmp) / "bulky.jpg"
            path.write_bytes(jpeg)
            self.assertEqual(read_exif_timestamp(path), datetime(2024, 6, 1, 12, 30, 45))
