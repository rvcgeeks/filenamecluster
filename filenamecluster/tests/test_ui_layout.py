"""Timeline geometry and calendar summaries, without opening a window."""

import unittest
from datetime import date, datetime, timedelta

from filetimecluster.core.cluster import Cluster
from filetimecluster.core.organize import name_clusters
from filetimecluster.core.parse import TimestampedFile
from filetimecluster.ui.calendar_view import month_weeks, shift_month, summarize_days
from filetimecluster.ui.layout import (
    MARGIN,
    MAX_WIDTH,
    MIN_BAR,
    MIN_PIXELS_PER_DAY,
    TimeScale,
    axis_ticks,
    file_marks,
    fit_pixels_per_day,
    layout_bars,
)


def events(*groups):
    return name_clusters(
        [
            Cluster(tuple(TimestampedFile(f"IMG_{when:%Y%m%d_%H%M%S}.jpg", when) for when in group))
            for group in groups
        ]
    )


DAY = datetime(2024, 1, 1)


class TimeScaleTests(unittest.TestCase):
    def test_positions_are_to_scale_and_invertible(self):
        scale = TimeScale(DAY, DAY + timedelta(days=10), 10)
        self.assertEqual(scale.x(DAY), MARGIN)
        self.assertEqual(scale.x(DAY + timedelta(days=3)), MARGIN + 30)
        self.assertEqual(scale.when(MARGIN + 15), DAY + timedelta(days=1, hours=12))
        self.assertEqual(scale.width, MARGIN + 100 + MARGIN)

    def test_zero_span_gets_a_minimum_and_bad_order_fails(self):
        scale = TimeScale(DAY, DAY, 24)
        self.assertEqual(scale.end, DAY + timedelta(hours=1))
        with self.assertRaises(ValueError):
            TimeScale(DAY, DAY - timedelta(days=1), 1)

    def test_zoom_is_clamped(self):
        long = TimeScale(DAY, DAY + timedelta(days=3650), 10_000)
        self.assertLessEqual(long.width, MAX_WIDTH + 1)
        tiny = TimeScale(DAY, DAY + timedelta(days=1), 0)
        self.assertEqual(tiny.pixels_per_day, MIN_PIXELS_PER_DAY)

    def test_fit_uses_the_available_width(self):
        ppd = fit_pixels_per_day(DAY, DAY + timedelta(days=10), 2 * MARGIN + 500)
        self.assertAlmostEqual(ppd, 50)


class BarTests(unittest.TestCase):
    def test_overlapping_labels_go_to_a_new_lane(self):
        clusters = events(
            [DAY, DAY + timedelta(hours=1)],
            [DAY + timedelta(days=3)],
            [DAY + timedelta(days=40)],
        )
        crowded = layout_bars(clusters, TimeScale(DAY, DAY + timedelta(days=40), 1))
        self.assertEqual([bar.lane for bar in crowded], [0, 1, 0])
        self.assertGreaterEqual(crowded[1].x1 - crowded[1].x0, MIN_BAR)

        roomy = layout_bars(clusters, TimeScale(DAY, DAY + timedelta(days=40), 100))
        self.assertEqual([bar.lane for bar in roomy], [0, 0, 0])

    def test_day_window_clips_and_drops_outside_clusters(self):
        clusters = events(
            [DAY - timedelta(hours=5), DAY + timedelta(hours=3)],
            [DAY + timedelta(days=5)],
        )
        scale = TimeScale(DAY, DAY + timedelta(days=1), 480)
        bars = layout_bars(clusters, scale)
        self.assertEqual([bar.index for bar in bars], [0])
        self.assertEqual(bars[0].x0, MARGIN)
        self.assertEqual(bars[0].x1, scale.x(DAY + timedelta(hours=3)))
        self.assertEqual(file_marks(clusters, scale), [round(scale.x(DAY + timedelta(hours=3)))])


class TickTests(unittest.TestCase):
    def test_levels_follow_the_zoom(self):
        span = (datetime(2015, 11, 1), datetime(2025, 10, 20))
        years = axis_ticks(TimeScale(*span, 0.1))
        self.assertIn("2020", [tick.label for tick in years if tick.major])
        self.assertTrue(all(tick.major for tick in years))

        with_months = axis_ticks(TimeScale(*span, 0.5))
        self.assertTrue(any(not tick.major for tick in with_months))

        months = axis_ticks(TimeScale(datetime(2024, 1, 5), datetime(2024, 3, 2), 10))
        labels = [tick.label for tick in months if tick.major]
        self.assertEqual(labels[-2:], ["Feb 2024", "Mar 2024"])
        self.assertTrue(all(tick.x >= 0 for tick in months))
        self.assertTrue(any(not tick.major for tick in months))

        december = axis_ticks(TimeScale(datetime(2023, 12, 1), datetime(2024, 1, 2), 2))
        self.assertIn("Jan 2024", [tick.label for tick in december])

        days = axis_ticks(TimeScale(DAY, DAY + timedelta(days=2), 100))
        self.assertEqual([t.label for t in days if t.major], ["01-01-2024", "02-01-2024", "03-01-2024"])
        hours = axis_ticks(TimeScale(DAY, DAY + timedelta(days=1), 480))
        self.assertEqual(len([t for t in hours if not t.major]), 23)

    def test_sparse_years_skip_labels(self):
        ticks = axis_ticks(TimeScale(datetime(2000, 1, 1), datetime(2040, 1, 1), 0.02))
        self.assertTrue(all(int(tick.label) % 8 == 0 for tick in ticks))


class CalendarDataTests(unittest.TestCase):
    def test_days_inside_an_event_are_filled(self):
        clusters = events(
            [DAY + timedelta(hours=10), DAY + timedelta(hours=11), DAY + timedelta(days=2)],
            [DAY + timedelta(days=9)],
        )
        days = summarize_days(clusters)
        self.assertEqual(days[date(2024, 1, 1)].files, 2)
        self.assertEqual(days[date(2024, 1, 2)].files, 0)
        self.assertEqual(days[date(2024, 1, 2)].cluster, 0)
        self.assertEqual(days[date(2024, 1, 10)].cluster, 1)
        self.assertNotIn(date(2024, 1, 5), days)

    def test_month_helpers(self):
        weeks = month_weeks(2024, 2)
        self.assertEqual(weeks[0][0], date(2024, 1, 29))
        self.assertTrue(all(len(week) == 7 for week in weeks))
        self.assertEqual(shift_month(2024, 12, 1), (2025, 1))
        self.assertEqual(shift_month(2024, 1, -1), (2023, 12))


if __name__ == "__main__":
    unittest.main()
