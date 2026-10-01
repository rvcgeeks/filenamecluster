"""A name clash starts unanswered."""

import unittest

from filenamecluster.ui.model import ClashChoice, NameClash


class ClashModelTests(unittest.TestCase):
    def test_a_new_clash_has_no_choice(self):
        clash = NameClash("a.jpg", 2)
        self.assertEqual(clash.name, "a.jpg")
        self.assertEqual(clash.count, 2)
        self.assertIsNone(clash.choice)
        self.assertFalse(clash.for_all)
        self.assertFalse(clash.cancelled)
        self.assertIs(ClashChoice.REPLACE, ClashChoice.REPLACE)
