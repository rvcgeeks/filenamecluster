"""Capture times read from video containers."""

import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from filenamecluster.core import cluster_directory, read_exif_timestamp

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

_UTC = datetime(2024, 6, 1, 12, 30, 45, tzinfo=timezone.utc)
_MAC = datetime(1904, 1, 1, tzinfo=timezone.utc)
_SECONDS = int((_UTC - _MAC).total_seconds())
_LOCAL = _UTC.astimezone().replace(tzinfo=None)
_OTHER = int((datetime(2019, 1, 1, tzinfo=timezone.utc) - _MAC).total_seconds())


def _box(kind: bytes, payload: bytes) -> bytes:
    return (len(payload) + 8).to_bytes(4, "big") + kind + payload


def _mvhd(seconds: int, version: int = 0) -> bytes:
    if version == 0:
        body = bytearray(100)
        body[4:8] = seconds.to_bytes(4, "big")
        body[8:12] = seconds.to_bytes(4, "big")
    else:
        body = bytearray(112)
        body[0] = 1
        body[4:12] = seconds.to_bytes(8, "big")
        body[12:20] = seconds.to_bytes(8, "big")
    body[12 if version == 0 else 20 : 16 if version == 0 else 24] = (1000).to_bytes(4, "big")
    return _box(b"mvhd", bytes(body))


def _mp4(seconds: int, *, exif: bytes | None = None, mdat_first: bool = False, version: int = 0) -> bytes:
    ftyp = _box(b"ftyp", b"mp42" + b"\x00\x00\x00\x00" + b"mp42" + b"isom")
    payload = b""
    if exif is not None:
        payload += _box(b"free", b"Exif\x00\x00" + exif)
    payload += _mvhd(seconds, version)
    movie = _box(b"moov", payload)
    media = _box(b"mdat", b"\x00" * 32)
    return ftyp + (media + movie if mdat_first else movie + media)


def _avi(idit: str, *, exif: bytes | None = None) -> bytes:
    chunks = b""
    if exif is not None:
        block = b"Exif\x00\x00" + exif
        chunks += b"strd" + len(block).to_bytes(4, "little") + block
        if len(block) % 2:
            chunks += b"\x00"
    text = idit.encode("ascii")
    chunks += b"IDIT" + len(text).to_bytes(4, "little") + text
    if len(text) % 2:
        chunks += b"\x00"
    listing = b"hdrl" + chunks
    chunk = b"LIST" + len(listing).to_bytes(4, "little") + listing
    body = b"AVI " + chunk
    return b"RIFF" + len(body).to_bytes(4, "little") + body

class VideoTimestampTests(unittest.TestCase):
    def test_container_clock_and_embedded_exif(self):
        wall = datetime(2024, 6, 1, 12, 30, 45)
        blobs = {
            "a.mp4": (_mp4(_SECONDS), _LOCAL),
            "b.mov": (_mp4(_SECONDS, mdat_first=True), _LOCAL),
            "c.m4v": (_mp4(_SECONDS, version=1), _LOCAL),
            "d.mp4": (_mp4(_OTHER, exif=_tiff(WHEN, OLDER)), wall),
            "e.avi": (_avi("Sat Jun 01 12:30:45 2024"), wall),
            "f.avi": (_avi("Wed Jan 01 00:00:00 2020", exif=_tiff(WHEN)), wall),
            "g.mov": (_box(b"moov", _mvhd(_SECONDS)), _LOCAL),
        }
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, (blob, expected) in blobs.items():
                (root / name).write_bytes(blob)
                self.assertEqual(read_exif_timestamp(root / name), expected, name)

    def test_only_pictures_and_videos_are_opened(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "notes.txt").write_bytes(b"hello Exif\x00\x00" + _tiff(WHEN))
            (root / "clip.mp4").write_bytes(_box(b"ftyp", b"mp42" + b"\x00" * 4))
            self.assertIsNone(read_exif_timestamp(root / "notes.txt"))
            self.assertIsNone(read_exif_timestamp(root / "clip.mp4"))

    def test_filename_wins_and_unreadable_media_is_skipped(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "VID_20240101_101500.mp4").write_bytes(_mp4(_OTHER))
            (root / "plain.mp4").write_bytes(_mp4(_SECONDS))
            (root / "broken.mp4").write_bytes(_box(b"ftyp", b"mp42" + b"\x00" * 4))
            (root / "notes.txt").write_bytes(b"Exif\x00\x00" + _tiff(WHEN))
            result = cluster_directory(root)
            found = {item.name: item.timestamp for cluster in result.clusters for item in cluster.files}
            self.assertEqual(found["VID_20240101_101500.mp4"], datetime(2024, 1, 1, 10, 15, 0))
            self.assertEqual(found["plain.mp4"], _LOCAL)
            self.assertEqual(set(result.ignored_without_timestamp), {"broken.mp4", "notes.txt"})

    def test_a_failed_read_is_still_skipped(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "plain.jpg").write_bytes(b"\xff\xd8\xff\xd9")
            with patch(
                "filenamecluster.core.operations.pipeline.read_exif_timestamp",
                side_effect=OSError("unreadable"),
            ):
                result = cluster_directory(root)
            self.assertEqual(result.clusters, ())
            self.assertEqual(result.ignored_without_timestamp, ("plain.jpg",))
