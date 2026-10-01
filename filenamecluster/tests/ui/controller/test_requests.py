"""Semantic requests stay catalog-neutral until the view translates them."""

import unittest
from pathlib import Path

from filenamecluster.ui.controller import Applied, Failure, FlattenAsk, Success, Wait


class RequestTests(unittest.TestCase):
    def test_a_disk_result_is_either_a_value_or_an_error(self):
        done = Success(4)
        failed = Failure(OSError("full"))
        self.assertEqual(done.value, 4)
        self.assertIsInstance(failed.error, OSError)
        self.assertEqual(Applied(files=2, events=1).files, 2)
        asked = FlattenAsk(folders=3, path=Path("album"))
        self.assertEqual(asked.folders, 3)
        self.assertEqual(asked.noted, 0)
        self.assertIs(Wait.OPEN, Wait.OPEN)
