"""OptionError carries a semantic fault and field, untranslated."""

import unittest

from filenamecluster.core.operations import OptionError, OptionFault, OptionField


class OptionErrorTests(unittest.TestCase):
    def test_fault_and_field_are_kept_for_the_view(self):
        error = OptionError(OptionFault.OUT_OF_RANGE, OptionField.MIN_YEAR, 1, 9999)
        self.assertIs(error.fault, OptionFault.OUT_OF_RANGE)
        self.assertIs(error.field, OptionField.MIN_YEAR)
        self.assertEqual((error.low, error.high), (1, 9999))
        self.assertEqual(str(error), "OUT_OF_RANGE")
        self.assertIsInstance(error, Exception)

    def test_a_fault_without_bounds_leaves_them_empty(self):
        error = OptionError(OptionFault.NOT_A_NUMBER, OptionField.FLOOR)
        self.assertIsNone(error.low)
        self.assertIsNone(error.high)
