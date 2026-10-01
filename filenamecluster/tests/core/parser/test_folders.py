"""Event-folder names may carry words before or after the stamp."""

import unittest

from filenamecluster.core.parser.folders import (
    event_folder_parts,
    folder_note,
    is_cluster_folder_name,
    name_with_note,
)

STAMP = "4 14-11-2015 16.48.30 to 15-11-2015 13.31.11"
SAME_DAY = "3 12-08-2026 22.34.11 to 23.10.00"


class FolderNameTests(unittest.TestCase):
    def test_a_plain_stamp_has_no_note(self):
        self.assertEqual(event_folder_parts(STAMP), ("", STAMP, ""))
        self.assertEqual(event_folder_parts(SAME_DAY), ("", SAME_DAY, ""))
        self.assertIsNone(folder_note(STAMP))
        self.assertTrue(is_cluster_folder_name(STAMP))

    def test_words_may_sit_before_or_after_the_stamp(self):
        prefix = f"Hyderabad trip {STAMP}"
        suffix = f"{STAMP} Hyderabad Trip"
        both = f"Hyderabad trip {SAME_DAY} evening"
        self.assertEqual(event_folder_parts(prefix), ("Hyderabad trip", STAMP, ""))
        self.assertEqual(event_folder_parts(suffix), ("", STAMP, "Hyderabad Trip"))
        self.assertEqual(folder_note(both), ("Hyderabad trip", "evening"))
        self.assertEqual(name_with_note("Hyderabad trip", STAMP, ""), prefix)
        self.assertEqual(name_with_note("", STAMP, "Hyderabad Trip"), suffix)
        self.assertEqual(name_with_note("Goa", SAME_DAY, "evening"), f"Goa {SAME_DAY} evening")

    def test_words_must_be_separated_from_the_stamp(self):
        self.assertIsNone(event_folder_parts(f"trip{STAMP}"))
        self.assertIsNone(event_folder_parts(f"{STAMP}Trip"))
        self.assertFalse(is_cluster_folder_name("album"))
        self.assertFalse(is_cluster_folder_name(".."))
        self.assertFalse(is_cluster_folder_name(""))
        self.assertIsNone(folder_note("album"))

    def test_extra_spaces_beside_the_stamp_still_match(self):
        name = f"Hyderabad trip  {STAMP}"
        self.assertEqual(folder_note(name), ("Hyderabad trip", ""))
        self.assertEqual(name_with_note("Hyderabad trip", STAMP, ""), f"Hyderabad trip {STAMP}")
