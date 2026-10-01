"""Built-in filename patterns and rules a caller supplies."""

import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from filenamecluster.core.parser import PatternRule, TimestampPatterns, parse_timestamp
from filenamecluster.core.parser.patterns import DEFAULT_RULES
from filenamecluster.core.operations.pipeline import cluster_directory

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

    def test_an_unknown_field_is_refused_and_a_missing_rule_can_be_added(self):
        with self.assertRaises(TypeError):
            TimestampPatterns(not_a_rule="x")
        key = DEFAULT_RULES[0].key
        added = TimestampPatterns(rules=(), **{key: "(?P<ms>\\d{13})"})
        self.assertEqual(getattr(added, key), "(?P<ms>\\d{13})")
        with self.assertRaises(AttributeError):
            added.not_a_field

    def test_an_extra_rule_is_used_alongside_the_built_in_ones(self):
        extra = PatternRule(
            "",
            "Shot prefix",
            r"shot(?P<y>\d{4})(?P<mo>\d{2})(?P<d>\d{2})(?P<h>\d{2})(?P<mi>\d{2})(?P<s>\d{2})",
        )
        patterns = TimestampPatterns(rules=TimestampPatterns().rules + (extra,))
        self.assertEqual(
            parse_timestamp("shot20240301120000.jpg", patterns),
            datetime(2024, 3, 1, 12, 0, 0),
        )
        self.assertEqual(
            parse_timestamp("IMG_20240101_101500.jpg", patterns),
            datetime(2024, 1, 1, 10, 15, 0),
        )
