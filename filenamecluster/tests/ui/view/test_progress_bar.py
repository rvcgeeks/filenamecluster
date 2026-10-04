"""The progress bar switches from an unknown wait to a fraction."""

import unittest

from filenamecluster.ui.view import bar_span


class ProgressBarTests(unittest.TestCase):
    def test_a_missing_total_stays_indeterminate_and_a_count_fills_the_bar(self):
        self.assertEqual(bar_span(0, 0), ("indeterminate", 0, 100))
        self.assertEqual(bar_span(2, 5), ("determinate", 2, 5))
        self.assertEqual(bar_span(9, 5), ("determinate", 5, 5))
