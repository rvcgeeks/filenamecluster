"""Built-in option rows."""

import unittest
from datetime import timedelta

from filenamecluster.ui.model import OptionFields


class OptionFieldsTests(unittest.TestCase):
    def test_hours_are_the_length_of_a_pause(self):
        self.assertEqual(OptionFields.hours(timedelta(hours=3)), 3)
        self.assertEqual(OptionFields.hours(timedelta(days=30)), 720)
