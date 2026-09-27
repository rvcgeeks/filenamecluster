"""EXIF capture times, used only when the filename has none."""

import unittest
import zlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from filenamecluster.core.exif import read_exif_timestamp
from filenamecluster.core.pipeline import cluster_directory

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
    def test_jpeg_png_webp_tiff_and_heif(self):
        expected = datetime(2024, 6, 1, 12, 30, 45)
        blobs = {
            "a.jpg": _jpeg(_tiff(WHEN, OLDER), tem=True),
            "b.png": _png(_tiff(WHEN, OLDER)),
            "c.webp": _webp(_tiff(WHEN, OLDER)),
            "d.tif": _tiff(WHEN, OLDER, endian="big"),
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
        import filenamecluster.core.exif as exif

        tiff = _tiff(WHEN)
        app1 = len(b"Exif\x00\x00" + tiff) + 2
        pad = b"\x00" * (app1 + 100)
        jpeg = b"\xff\xd8"
        jpeg += b"\xff\xe0" + (len(pad) + 2).to_bytes(2, "big") + pad
        payload = b"Exif\x00\x00" + tiff
        jpeg += b"\xff\xe1" + (len(payload) + 2).to_bytes(2, "big") + payload + b"\xff\xd9"
        original = exif._MAX_SEGMENT
        exif._MAX_SEGMENT = app1 + 10
        try:
            with TemporaryDirectory() as tmp:
                path = Path(tmp) / "bulky.jpg"
                path.write_bytes(jpeg)
                self.assertEqual(read_exif_timestamp(path), datetime(2024, 6, 1, 12, 30, 45))
        finally:
            exif._MAX_SEGMENT = original

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
                "filenamecluster.core.pipeline.read_exif_timestamp",
                side_effect=OSError("unreadable"),
            ):
                result = cluster_directory(root)
            self.assertEqual(result.clusters, ())
            self.assertEqual(result.ignored_without_timestamp, ("plain.jpg",))


class PdfTimestampTests(unittest.TestCase):
    def test_pdf_info_and_xmp_creation_dates(self):
        xmp_utc = datetime(2024, 6, 1, 12, 30, 45, tzinfo=timezone.utc)
        expected_local = xmp_utc.astimezone().replace(tzinfo=None)
        blobs = {
            "info.pdf": (
                b"%PDF-1.7\n1 0 obj\n<< /CreationDate (D:20240601123045) >>\nendobj\n%%EOF",
                datetime(2024, 6, 1, 12, 30, 45),
            ),
            "xmp.pdf": (
                b'%PDF-1.7\n<xmp:CreateDate="2024-06-01T12:30:45Z"/>',
                expected_local,
            ),
        }
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, (blob, expected) in blobs.items():
                (root / name).write_bytes(blob)
                self.assertEqual(read_exif_timestamp(root / name), expected, name)

    def test_pdf_creation_date_can_be_near_the_end(self):
        import filenamecluster.core.exif as exif

        original = exif._MAX_READ
        exif._MAX_READ = 64
        try:
            with TemporaryDirectory() as tmp:
                path = Path(tmp) / "tail.pdf"
                path.write_bytes(
                    b"%PDF-1.7\n"
                    + b"x" * 200
                    + b"\n/CreationDate (D:20240601123045+05'30')\n%%EOF"
                )
                source = datetime(
                    2024, 6, 1, 12, 30, 45, tzinfo=timezone(timedelta(hours=5, minutes=30))
                )
                self.assertEqual(
                    read_exif_timestamp(path),
                    source.astimezone().replace(tzinfo=None),
                )
        finally:
            exif._MAX_READ = original

    def test_pdf_filename_wins_and_missing_metadata_is_skipped(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            metadata = b"%PDF-1.7\n<< /CreationDate (D:20110202030405) >>\n%%EOF"
            (root / "scan_20240101_101500.pdf").write_bytes(metadata)
            (root / "plain.pdf").write_bytes(
                b"%PDF-1.7\n<< /CreationDate (D:20240601123045) >>\n%%EOF"
            )
            (root / "missing.pdf").write_bytes(b"%PDF-1.7\n%%EOF")
            (root / "notes.txt").write_bytes(
                b"/CreationDate (D:20240601123045)"
            )
            result = cluster_directory(root)
            found = {item.name: item.timestamp for cluster in result.clusters for item in cluster.files}
            self.assertEqual(
                found["scan_20240101_101500.pdf"],
                datetime(2024, 1, 1, 10, 15),
            )
            self.assertEqual(found["plain.pdf"], datetime(2024, 6, 1, 12, 30, 45))
            self.assertEqual(set(result.ignored_without_timestamp), {"missing.pdf", "notes.txt"})

    def test_invalid_and_out_of_range_pdf_dates_are_ignored(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            values = {
                "bad.pdf": b"%PDF-1.7\n/CreationDate (not-a-date)",
                "old.pdf": b"%PDF-1.7\n/CreationDate (D:19800101000000)",
                "invalid.pdf": b"%PDF-1.7\n/CreationDate (D:20241340000000)",
            }
            for name, blob in values.items():
                path = root / name
                path.write_bytes(blob)
                self.assertIsNone(read_exif_timestamp(path), name)


if __name__ == "__main__":
    unittest.main()
