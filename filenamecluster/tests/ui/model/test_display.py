"""Display values: semantic status and calendar ownership."""

import unittest
from dataclasses import replace
from datetime import date, datetime, timedelta

from filenamecluster.core.algorithm import Cluster
from filenamecluster.core.operations.organize import name_clusters
from filenamecluster.core.parser import TimestampedFile
from filenamecluster.ui.model import LearnedKind, LearnedSummary, SummaryStatus, cover_days


def events(*groups):
    return name_clusters(
        [
            Cluster(
                tuple(
                    TimestampedFile(
                        f"IMG_{when:%Y%m%d_%H%M%S}.jpg",
                        when,
                    )
                    for when in group
                )
            )
            for group in groups
        ]
    )


class DisplayTests(unittest.TestCase):
    def test_days_inside_an_event_are_filled(self):
        start = datetime(2024, 1, 1)
        clusters = events(
            [
                start + timedelta(hours=10),
                start + timedelta(hours=11),
                start + timedelta(days=2),
            ],
            [start + timedelta(days=9)],
        )
        days = cover_days(clusters)
        self.assertEqual(days[date(2024, 1, 1)].files, 2)
        self.assertEqual(days[date(2024, 1, 2)].files, 0)
        self.assertEqual(days[date(2024, 1, 2)].cluster, 0)
        self.assertEqual(days[date(2024, 1, 10)].cluster, 1)
        self.assertNotIn(date(2024, 1, 5), days)

    def test_status_copies_its_semantic_fields(self):
        status = SummaryStatus(
            events=1,
            files=3,
            missing=0,
            event_folders=0,
            other_folders=0,
            learned=LearnedSummary(LearnedKind.NONE),
            left_out=0,
        )
        changed = replace(status, files=9)
        self.assertEqual(status.files, 3)
        self.assertEqual(changed.files, 9)
