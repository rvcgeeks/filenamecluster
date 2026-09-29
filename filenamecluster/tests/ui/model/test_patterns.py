"""PatternRow stores whether a filename expression can be compiled."""

import unittest

from filenamecluster.core.parser import TimestampPatterns
from filenamecluster.ui.model import PatternRow


class PatternRowTests(unittest.TestCase):
    def test_a_builtin_expression_is_usable(self):
        row = PatternRow("clock", "clock", "Dashed clock", TimestampPatterns().clock_separated, False)
        self.assertFalse(row.invalid)

    def test_a_blank_expression_is_turned_off(self):
        row = PatternRow("off", "", "Off", "   ", False)
        self.assertFalse(row.invalid)

    def test_an_expression_that_does_not_compile_is_invalid(self):
        row = PatternRow("broken", "", "Broken", "(", False)
        self.assertTrue(row.invalid)

    def test_an_expression_without_time_groups_is_invalid(self):
        row = PatternRow("plain", "", "No groups", r"IMG_\d+", False)
        self.assertTrue(row.invalid)
