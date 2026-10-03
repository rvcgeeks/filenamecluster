"""PDF CreationDate metadata."""

import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from filenamecluster.core import cluster_directory, read_exif_timestamp

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
        with (
            patch("filenamecluster.core.exif.pdf._MAX_READ", 64),
            TemporaryDirectory() as tmp,
        ):
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
