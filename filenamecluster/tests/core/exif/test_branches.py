"""Error branches in picture, video, and PDF clocks."""

import unittest
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from datetime import tzinfo

from filenamecluster.core import (
    _MAX_READ,
    _MAX_SEGMENT,
    _ascii_at,
    _avi_timestamp,
    _bmff_timestamp,
    _box_header,
    _datetime_from_tiff,
    _jpeg_exif,
    _jpeg_marker,
    _mvhd_in,
    _mvhd_time,
    _parse_clock,
    _parse_idit,
    _parse_pdf_date,
    _pdf_date_after,
    _pdf_timestamp,
    _png_exif,
    _search_exif_header,
    _time_in_block,
    _u16,
    _u32,
    _walk_ifd,
    _webp_exif,
    read_exif_timestamp,
)


class ImageBranchTests(unittest.TestCase):
    def test_broken_containers_have_no_exif_block(self):
        self.assertIsNone(_jpeg_marker(BytesIO(b"\x00")))
        self.assertIsNone(_jpeg_marker(BytesIO(b"\xff")))
        self.assertIsNone(_jpeg_exif(BytesIO(b"\x00\x00")))
        self.assertIsNone(_jpeg_exif(BytesIO(b"\xff\xd8\xff\xd9")))
        self.assertIsNone(_jpeg_exif(BytesIO(b"\xff\xd8\xff\xe0\x00\x01")))
        self.assertIsNone(_jpeg_exif(BytesIO(b"\xff\xd8\xff\xe1\x00\x0a\x00\x00")))
        self.assertIsNone(_png_exif(BytesIO(b"not a png")))
        self.assertIsNone(_png_exif(BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00\x00")))
        short = b"\x89PNG\r\n\x1a\n" + (5).to_bytes(4, "big") + b"eXIf" + b"\x00"
        self.assertIsNone(_png_exif(BytesIO(short)))
        self.assertIsNone(_webp_exif(BytesIO(b"not a webp!!")))
        self.assertIsNone(_webp_exif(BytesIO(b"RIFF" + b"\x00" * 4 + b"WEBP" + b"EX")))
        huge = (_MAX_SEGMENT + 1).to_bytes(4, "little")
        self.assertIsNone(_webp_exif(BytesIO(b"RIFF" + b"\x00" * 4 + b"WEBP" + b"EXIF" + huge)))
        self.assertIsNone(_webp_exif(BytesIO(b"RIFF" + b"\x00" * 4 + b"WEBP" + b"EXIF" + (4).to_bytes(4, "little") + b"x")))
        plain = b"RIFF" + b"\x00" * 4 + b"WEBP" + b"EXIF" + (4).to_bytes(4, "little") + b"data"
        self.assertEqual(_webp_exif(BytesIO(plain)), b"data")
        self.assertIsNone(_search_exif_header(BytesIO(b"x" * 10)))
        self.assertIsNone(_search_exif_header(BytesIO(b"x" * (_MAX_READ + 10))))


class TiffBranchTests(unittest.TestCase):
    def test_a_damaged_block_has_no_clock(self):
        self.assertIsNone(_datetime_from_tiff(b"short", 1990, 2100))
        self.assertIsNone(_datetime_from_tiff(b"II" + b"\x00\x00" + b"\x00" * 8, 1990, 2100))
        self.assertIsNone(_parse_clock("2024", 1990, 2100))
        self.assertIsNone(_u16(b"\x00", 0, "little"))
        self.assertIsNone(_u32(b"\x00\x00", 0, "little"))
        found: dict[int, str] = {}
        _walk_ifd(b"II", 0, "little", found, set(), 0)
        data = b"\x00\x00" + (600).to_bytes(2, "little")
        _walk_ifd(data, 0, "little", found, set(), 0)
        self.assertEqual(_ascii_at(b"\x00" * 8 + b"Hi\x00\x00", 0, 3, "little"), "Hi")
        short = (2).to_bytes(2, "little") + b"\x00" * 10
        _walk_ifd(short, 0, "little", found, set(), 0)
        far = bytearray(12)
        far[8:12] = (100).to_bytes(4, "little")
        self.assertEqual(_ascii_at(bytes(far), 0, 8, "little"), "")


class PdfBranchTests(unittest.TestCase):
    def test_quoted_escaped_and_zoned_dates(self):
        escaped = b"%PDF-1.7\n/CreationDate (D:20240601123045\\))"
        quoted = b"%PDF-1.7\n/CreationDate >2024-06-01T12:30:45<"
        zulu = b"%PDF-1.7\n/CreationDate (D:20240601123045Z)"
        plain = b"%PDF-1.7\n/CreationDate (hello)"
        self.assertIsNotNone(_pdf_timestamp(BytesIO(escaped), 1990, 2100))
        self.assertIsNotNone(_pdf_timestamp(BytesIO(quoted), 1990, 2100))
        self.assertIsNotNone(_pdf_timestamp(BytesIO(zulu), 1990, 2100))
        self.assertIsNone(_pdf_timestamp(BytesIO(plain), 1990, 2100))
        self.assertIsNone(_parse_pdf_date("not a date", 1990, 2100))
        self.assertEqual(_pdf_date_after(b"/CreationDate >unterminated", len(b"/CreationDate")), "")

        class Broken(tzinfo):
            def utcoffset(self, dt):
                raise OSError("no zone")

            def dst(self, dt):
                return timedelta(0)

            def tzname(self, dt):
                return "broken"

        with patch("filenamecluster.core.exif.pdf.timezone", return_value=Broken()):
            self.assertIsNone(_parse_pdf_date("D:20240601123045+0530", 1990, 2100))


class VideoBranchTests(unittest.TestCase):
    def test_short_and_oversized_boxes_stop(self):
        self.assertIsNone(_bmff_timestamp(BytesIO((40).to_bytes(4, "big") + b"moov" + b"xx"), 1990, 2100))
        self.assertIsNone(_box_header(BytesIO((1).to_bytes(4, "big") + b"free" + b"xx")))
        large = (1).to_bytes(4, "big") + b"free" + (24).to_bytes(8, "big") + b"12345678"
        self.assertIsNotNone(_box_header(BytesIO(large)))
        self.assertIsNotNone(_box_header(BytesIO((0).to_bytes(4, "big") + b"free" + b"abcd")))
        self.assertIsNone(_box_header(BytesIO((4).to_bytes(4, "big") + b"free")))
        self.assertIsNone(_mvhd_in((8).to_bytes(4, "big") + b"free", 1990, 2100))
        wide = (1).to_bytes(4, "big") + b"mvhd" + (24).to_bytes(8, "big") + b"\x00" * 8
        self.assertIsNone(_mvhd_in(wide, 1990, 2100))
        self.assertIsNone(_mvhd_in((4).to_bytes(4, "big") + b"mvhd", 1990, 2100))
        self.assertIsNone(_mvhd_time(b"", 1990, 2100))
        self.assertIsNone(_mvhd_time(b"\x02" + b"\x00" * 12, 1990, 2100))
        self.assertIsNone(_mvhd_time(b"\x00" + b"\x00" * 8, 1990, 2100))
        huge = bytearray(20)
        huge[0] = 1
        huge[4:12] = (10**18).to_bytes(8, "big")
        self.assertIsNone(_mvhd_time(bytes(huge), 1990, 2100))
        late = int(
            (
                datetime(2200, 1, 1, tzinfo=timezone.utc)
                - datetime(1904, 1, 1, tzinfo=timezone.utc)
            ).total_seconds()
        )
        body = bytearray(20)
        body[0] = 1
        body[4:12] = late.to_bytes(8, "big")
        self.assertIsNone(_mvhd_time(bytes(body), 1990, 2100))

    def test_avi_lists_idit_and_a_short_read(self):
        text = b"Sat Jun 01 12:30:45 2024\x00"
        movi = b"movi" + b"xxxx"
        listing = b"LIST" + len(movi).to_bytes(4, "little") + movi
        idit = b"IDIT" + len(text).to_bytes(4, "little") + text + b"\x00"
        blob = b"RIFF" + b"\x00" * 4 + b"AVI " + listing + idit
        found = _avi_timestamp(BytesIO(blob), 1990, 2100)
        self.assertEqual(found, datetime(2024, 6, 1, 12, 30, 45))
        nested = b"INFO" + b"IDIT" + len(text).to_bytes(4, "little") + text
        data = b"LIST" + len(nested).to_bytes(4, "little") + nested
        self.assertEqual(_time_in_block(data, 1990, 2100), datetime(2024, 6, 1, 12, 30, 45))
        self.assertIsNone(_time_in_block(b"IDIT" + (20).to_bytes(4, "little") + b"short", 1990, 2100))
        self.assertIsNone(_parse_idit(b"not a date", 1990, 2100))
        self.assertIsNone(_parse_idit(b"Tue Jan 01 00:00:00 1980", 1990, 2100))
        junk = b"JUNK" + (1).to_bytes(4, "little") + b"Z\x00"
        plain = b"RIFF" + b"\x00" * 4 + b"AVI " + junk
        self.assertIsNone(_avi_timestamp(BytesIO(plain), 1990, 2100))
        self.assertIsNone(_time_in_block(b"JUNK" + (0).to_bytes(4, "little"), 1990, 2100))

        class Short:
            def __init__(self):
                self.pos = 0

            def seek(self, offset, whence=0):
                if whence == 2:
                    self.pos = 20
                else:
                    self.pos = offset

            def tell(self):
                return self.pos

            def read(self, _count):
                if self.pos < 12:
                    self.pos = 12
                    return b"x" * 12
                self.pos += 3
                return b"abc"

        self.assertIsNone(_avi_timestamp(Short(), 1990, 2100))


class ReadBranchTests(unittest.TestCase):
    def test_a_raised_read_is_skipped(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "photo.jpg"
            path.write_bytes(b"\xff\xd8" + b"\x00" * 20)
            with patch("filenamecluster.core.exif.read._exif_payload", side_effect=RuntimeError):
                self.assertIsNone(read_exif_timestamp(path))
            path.write_bytes(b"II" + b"\x00" * 20)
            with patch("filenamecluster.core.exif.read._datetime_from_tiff", side_effect=RuntimeError):
                self.assertIsNone(read_exif_timestamp(path))
