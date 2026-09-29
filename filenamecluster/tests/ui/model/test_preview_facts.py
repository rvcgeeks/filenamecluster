"""PreviewFacts: skipped reasons, learned cells, and the buttons a scan enables."""

import unittest
from datetime import datetime

from filenamecluster.core.algorithm.cluster import ClusterParams
from filenamecluster.core.algorithm import GapModel
from filenamecluster.core.operations.organize import cluster_name
from filenamecluster.core.operations.pipeline import ClusterResult
from filenamecluster.ui.model import AppModel, SkippedReason


class PreviewFactTests(unittest.TestCase):
    def test_nothing_is_loaded_before_a_preview(self):
        model = AppModel()
        self.assertEqual(model.skipped(), ((), ()))
        self.assertTrue(all(value is None for _key, value in model.learned_cells()))

    def test_skipped_rows_name_the_reason_and_a_scan_sets_the_buttons(self):
        model = AppModel()
        event = cluster_name(1, datetime(2024, 1, 1, 10), datetime(2024, 1, 1, 11))
        model.remember_preview(
            ClusterResult(
                clusters=(),
                ignored_without_timestamp=("notes.txt",),
                ignored_directories=("album", event),
                params=ClusterParams(),
            )
        )
        folders, files = model.skipped()
        self.assertEqual(
            folders,
            (
                ("album", SkippedReason.SUBFOLDER),
                (event, SkippedReason.EVENT_FOLDER),
            ),
        )
        self.assertEqual(files, (("notes.txt", SkippedReason.NO_TIMESTAMP),))
        self.assertFalse(model.apply_enabled)
        self.assertTrue(model.flatten_enabled)
        self.assertEqual(model.status.event_folders, 1)
        self.assertEqual(model.status.other_folders, 1)
        self.assertEqual(
            [value for _key, value in model.learned_cells()],
            ["null", "null", "null", "null"],
        )

    def test_learned_numbers_match_the_file(self):
        model = AppModel()
        learned = GapModel(1.5, 9.0, 4.0, True)
        model.remember_preview(ClusterResult(
            clusters=(),
            ignored_without_timestamp=(),
            ignored_directories=(),
            params=ClusterParams(),
            model=learned,
        ))
        cells = dict(model.learned_cells())
        self.assertEqual(cells["within_hours"], "1.5")
        self.assertEqual(cells["separated"], "true")
