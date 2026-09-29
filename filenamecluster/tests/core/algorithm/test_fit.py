"""The fitted event boundary."""

import math
import unittest

from filenamecluster.core.algorithm import fit

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
