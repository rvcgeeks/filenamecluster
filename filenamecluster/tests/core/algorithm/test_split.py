"""The pause decision: floor, ceiling, learned boundary, and the 36-hour fallback."""

import unittest

from filenamecluster.core import FALLBACK_HOURS, split


class SplitTests(unittest.TestCase):
    def test_floor_and_ceiling_override_the_boundary(self):
        self.assertFalse(split(2, 3, 720, 40))
        self.assertFalse(split(3, 3, 720, 1))
        self.assertTrue(split(720, 3, 720, 1))
        self.assertTrue(split(800, 3, 720, 1))

    def test_the_boundary_decides_the_middle(self):
        self.assertFalse(split(39, 3, 720, 40))
        self.assertTrue(split(40, 3, 720, 40))

    def test_without_a_boundary_a_day_and_a_half_splits(self):
        self.assertEqual(FALLBACK_HOURS, 36)
        self.assertFalse(split(2, 3, 720, None))
        self.assertFalse(split(35, 3, 720, None))
        self.assertTrue(split(36, 3, 720, None))
        self.assertTrue(split(10, 3, 10, None))
