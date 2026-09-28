"""Calendar month geometry and day summaries, without opening a window."""

import unittest
from datetime import date, datetime, timedelta

from filenamecluster.core.cluster import Cluster
from filenamecluster.core.organize import name_clusters
from filenamecluster.core.parse import TimestampedFile
from filenamecluster.ui.view.calendar import month_weeks, shift_month, summarize_days


def events(*groups):
    return name_clusters(
        [
            Cluster(tuple(TimestampedFile(f"IMG_{when:%Y%m%d_%H%M%S}.jpg", when) for when in group))
            for group in groups
        ]
    )


DAY = datetime(2024, 1, 1)


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

