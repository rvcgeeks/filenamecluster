"""The fitted event boundary."""

import math
import unittest

from filenamecluster.core import _VARIANCE_FLOOR, _boundary, _variance, fit

class LearnTests(unittest.TestCase):
    def test_two_patterns_meet_between_their_centers(self):
        short = [math.log(hours) for hours in (0.2, 0.3, 0.5, 1, 2, 3)]
        long = [math.log(hours) for hours in (40, 50, 70, 90, 120)]
        model = fit(short + long)
        self.assertIsNotNone(model)
        assert model is not None
        self.assertTrue(model.separated)
        self.assertLess(model.within_hours, model.boundary_hours)
        self.assertLess(model.boundary_hours, model.between_hours)
        self.assertFalse(model.splits(2, 3, 24 * 30))
        self.assertTrue(model.splits(80, 3, 24 * 30))

    def test_too_few_gaps_are_not_a_model(self):
        self.assertIsNone(fit([0.0, 1.0, 2.0]))

    def test_pinned_gaps_collapse_or_swap(self):
        collapsed = fit([], [0.1, 0.2, 0.3, 0.4], [])
        self.assertIsNotNone(collapsed)
        other = fit([], [], [0.1, 0.2, 0.3, 0.4])
        self.assertIsNotNone(other)
        swapped = fit([], [math.log(80), math.log(90)], [math.log(1), math.log(2)])
        self.assertIsNotNone(swapped)
        assert swapped is not None
        self.assertLess(swapped.within_hours, swapped.between_hours)
        single = fit([0.1, 5.0], [1.0], [2.0])
        self.assertIsNotNone(single)

    def test_the_boundary_falls_back_when_the_curves_do_not_cross(self):
        outside = _boundary(0.0, 1.0, 0.5, 1.0, 1.0, 0.5)
        self.assertEqual(outside, 0.5)
        missing = _boundary(0.0, 0.2, 1e-6, 0.01, 5.0, 1.0 - 1e-6)
        self.assertEqual(missing, 0.005)
        self.assertEqual(_variance([1.0], 1.0), _VARIANCE_FLOOR)
