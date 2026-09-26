"""Timestamp and listing parsing."""

import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from filetimecluster.core.parse import TimestampPatterns, parse_timestamp, scan_directory
from filetimecluster.core.pipeline import cluster_directory


class ParseTimestampTests(unittest.TestCase):
    def test_camera_names(self):
        cases = {
            "IMG_20240101_101500.jpg": datetime(2024, 1, 1, 10, 15, 0),
            "VID_20201116_172025_HSR_120.mp4": datetime(2020, 11, 16, 17, 20, 25),
            "PANO_20151111_200758.jpg": datetime(2015, 11, 11, 20, 7, 58),
            "20191223_214548.mp4": datetime(2019, 12, 23, 21, 45, 48),
            "IMG_20200317_150503_BURST1.jpg": datetime(2020, 3, 17, 15, 5, 3),
            "IMG_20240126_102756_996.jpg": datetime(2024, 1, 26, 10, 27, 56),
            "VID_20160418_120823.mp4.tmp": datetime(2016, 4, 18, 12, 8, 23),
            "VID_20200420_140134(0)~2.mp4": datetime(2020, 4, 20, 14, 1, 34),
            "BeautyPlus_20160406180905_save.jpg": datetime(2016, 4, 6, 18, 9, 5),
            "BeautyPlus_20160911194950_save~2.jpg": datetime(2016, 9, 11, 19, 49, 50),
            "BeautyPlus_20191126183734953_save.jpg": datetime(
                2019, 11, 26, 18, 37, 34, 953000
            ),
            "Screenshot_2019-08-14-09-26-13-264_lockscreen.png": datetime(
                2019, 8, 14, 9, 26, 13, 264000
            ),
            "2016-05-10-12-21-48-870.jpg": datetime(2016, 5, 10, 12, 21, 48, 870000),
            "InShot_20240127_220124404.mp4": datetime(2024, 1, 27, 22, 1, 24, 404000),
            "Project_12_02_2023-12-03-01-32-06.mp4": datetime(2023, 12, 3, 1, 32, 6),
            "IMG-20240530-WA0014.jpg": datetime(2024, 5, 30, 0, 0, 0),
            "photo_2024-05-30.jpg": datetime(2024, 5, 30, 0, 0, 0),
            "IMG_20160229_100000.jpg": datetime(2016, 2, 29, 10, 0, 0),
        }
        for name, expected in cases.items():
            with self.subTest(name=name):
                self.assertEqual(parse_timestamp(name), expected)

    def test_partial_milliseconds(self):
        self.assertEqual(
            parse_timestamp("X20240127_22012440.jpg"),
            datetime(2024, 1, 27, 22, 1, 24, 400000),
        )
        self.assertEqual(
            parse_timestamp("X20240127_2201244.jpg"),
            datetime(2024, 1, 27, 22, 1, 24, 400000),
        )

    def test_calendar_clock_beats_trailing_epoch(self):
        # The trailing 13 digits are an export id about 90 minutes later.
        self.assertEqual(
            parse_timestamp("IMG_20191207_212826_1575739330128.jpg"),
            datetime(2019, 12, 7, 21, 28, 26),
        )
        self.assertEqual(
            parse_timestamp("VID_20201226_131553_exported_25506_1608996716093.jpg"),
            datetime(2020, 12, 26, 13, 15, 53),
        )

    def test_epoch_milliseconds_use_local_time(self):
        millis = 1462863402727
        self.assertEqual(
            parse_timestamp("img1462863402727.jpg"),
            datetime.fromtimestamp(millis / 1000.0),
        )
        self.assertEqual(
            parse_timestamp("PhotoGrid_1581064265269.jpg"),
            datetime.fromtimestamp(1581064265269 / 1000.0),
        )

    def test_epoch_outside_camera_years_is_ignored(self):
        self.assertIsNone(parse_timestamp("img0000000000000.jpg"))
        self.assertIsNone(parse_timestamp("img9999999999999.jpg"))

    def test_epoch_overflow_is_ignored(self):
        from filetimecluster.core.parse import _from_epoch_millis

        self.assertIsNone(_from_epoch_millis(10**30, 1990, 2100))

    def test_day_month_year_and_month_day_year(self):
        self.assertEqual(
            parse_timestamp("CamScanner 11-21-2024 12.22.jpg"),
            datetime(2024, 11, 21, 12, 22, 0),
        )
        self.assertEqual(
            parse_timestamp("scan 21-11-2024 12.22.33.jpg"),
            datetime(2024, 11, 21, 12, 22, 33),
        )
        # Both readings are valid; day-month-year wins.
        self.assertEqual(
            parse_timestamp("scan 03-04-2024 08.09.jpg"),
            datetime(2024, 4, 3, 8, 9, 0),
        )
        self.assertIsNone(parse_timestamp("scan 21-21-2024 12.22.jpg"))

    def test_names_without_a_capture_time(self):
        rejected = [
            "plain-name.mp4",
            ".escheck.tmp",
            "06be3c8e9fbd4c67954114367c696add.mp4",
            "0ce2e157cefa4d92b258a210e8c12dbe.mp4",
            "DaSr70bB1F3XK9Kf8Q0040Q8.jpg",
            "recording (1965).mp4",
            "clip 28 March 2022.mp4",
            "IMG_20191340_250199.jpg",
            "IMG_20190229_100000.jpg",
            "IMG_18990101_120000.jpg",
            "notes.txt",
            "",
        ]
        for name in rejected:
            with self.subTest(name=name):
                self.assertIsNone(parse_timestamp(name))

    def test_path_uses_the_filename_only(self):
        self.assertEqual(
            parse_timestamp("holiday/IMG_20240101_101500.jpg"),
            datetime(2024, 1, 1, 10, 15, 0),
        )


class ScanDirectoryTests(unittest.TestCase):
    def test_reads_only_the_top_level(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "IMG_20240101_100000.jpg").write_bytes(b"a")
            (root / "notes.txt").write_bytes(b"b")
            nested = root / "album"
            nested.mkdir()
            (nested / "IMG_20240102_100000.jpg").write_bytes(b"c")
            listing = scan_directory(root)
            self.assertEqual(
                listing.files,
                ("IMG_20240101_100000.jpg", "notes.txt"),
            )
            self.assertEqual(listing.directories, ("album",))

    def test_rejects_a_file(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "names.txt"
            path.write_text("IMG_20240101_100000.jpg\n", encoding="utf-8")
            with self.assertRaises(NotADirectoryError):
                scan_directory(path)


class PatternOptionTests(unittest.TestCase):
    def test_defaults_are_the_built_in_patterns(self):
        self.assertEqual(parse_timestamp("IMG_20240101_101500.jpg"), datetime(2024, 1, 1, 10, 15, 0))
        self.assertEqual(
            parse_timestamp("IMG_20240101_101500.jpg", TimestampPatterns()),
            datetime(2024, 1, 1, 10, 15, 0),
        )

    def test_year_window_and_priority_can_change(self):
        narrow = TimestampPatterns(min_year=2020, max_year=2021)
        self.assertIsNone(parse_timestamp("IMG_20150101_101500.jpg", narrow))
        self.assertEqual(
            parse_timestamp("IMG_20200101_101500.jpg", narrow),
            datetime(2020, 1, 1, 10, 15, 0),
        )
        date_wins = TimestampPatterns(prec_clock=1, prec_date=50)
        self.assertEqual(
            parse_timestamp("IMG_20240101_101500.jpg", date_wins),
            datetime(2024, 1, 1, 0, 0, 0),
        )
        with self.assertRaises(ValueError):
            TimestampPatterns(min_year=2020, max_year=1990)
        with self.assertRaises(ValueError):
            TimestampPatterns(prec_epoch=-1)

    def test_a_blank_pattern_is_off_and_a_custom_one_is_used(self):
        only_custom = TimestampPatterns(
            clock_separated="",
            clock_compact_sep="",
            clock_compact_17="",
            clock_compact_14=(
                r"shot(?P<y>\d{4})(?P<mo>\d{2})(?P<d>\d{2})"
                r"(?P<h>\d{2})(?P<mi>\d{2})(?P<s>\d{2})"
            ),
            numeric_date="",
            epoch_ms="",
            date_only="",
        )
        self.assertIsNone(parse_timestamp("IMG_20240101_101500.jpg", only_custom))
        self.assertEqual(
            parse_timestamp("shot20240101101500.jpg", only_custom),
            datetime(2024, 1, 1, 10, 15, 0),
        )
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "shot20240101101500.jpg").write_bytes(b"a")
            (root / "IMG_20240101_101500.jpg").write_bytes(b"b")
            result = cluster_directory(root, patterns=only_custom)
            self.assertEqual([item.name for item in result.clusters[0].files], ["shot20240101101500.jpg"])
            self.assertEqual(result.ignored_without_timestamp, ("IMG_20240101_101500.jpg",))

    def test_bad_patterns_are_rejected(self):
        with self.assertRaises(ValueError) as invalid:
            TimestampPatterns(clock_separated="(").compile()
        self.assertIn("Dashed clock", str(invalid.exception))
        with self.assertRaises(ValueError) as missing:
            TimestampPatterns(epoch_ms=r"\d+").compile()
        self.assertIn("missing named groups", str(missing.exception))

    def test_a_millisecond_group_of_the_wrong_length_is_skipped(self):
        patterns = TimestampPatterns(
            clock_separated="",
            clock_compact_sep="",
            clock_compact_17="",
            clock_compact_14=(
                r"(?P<y>\d{4})(?P<mo>\d{2})(?P<d>\d{2})"
                r"(?P<h>\d{2})(?P<mi>\d{2})(?P<s>\d{2})(?P<ms>\d{4})"
            ),
            numeric_date="",
            epoch_ms="",
            date_only="",
        )
        self.assertIsNone(parse_timestamp("202401011015009999", patterns))


if __name__ == "__main__":
    unittest.main()
