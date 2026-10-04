"""The progress meter counts steps only while a job is bound."""

import unittest

from filenamecluster.core import Meter, bind, expect, tick, unbind


class ProgressTests(unittest.TestCase):
    def test_ticks_move_the_bound_meter_and_stop_at_the_total(self):
        meter = Meter()
        self.assertEqual(meter.read(), (0, 0))
        expect(3)
        tick()
        self.assertEqual(meter.read(), (0, 0))
        token = bind(meter)
        try:
            expect(3)
            tick()
            tick(4)
            self.assertEqual(meter.read(), (3, 3))
        finally:
            unbind(token)
        tick()
        self.assertEqual(meter.read(), (3, 3))
