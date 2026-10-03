"""PreviewFacts: skipped reasons, learned cells, and the buttons a scan enables."""

import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from filenamecluster.core import ClusterParams, ClusterResult, GapModel, cluster_directory, cluster_name
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
        self.assertEqual(folders, (("album", SkippedReason.SUBFOLDER),))
        self.assertNotIn(event, [name for name, _reason in folders])
        self.assertEqual(files, (("notes.txt", SkippedReason.NO_TIMESTAMP),))
        self.assertFalse(model.apply_enabled)
        self.assertTrue(model.flatten_enabled)
        self.assertEqual(model.status.event_folders, 1)
        self.assertEqual(model.status.other_folders, 1)
        self.assertEqual(
            [value for _key, value in model.learned_cells()],
            ["null", "null", "null", "null"],
        )

    def test_an_already_clustered_folder_is_left_off_the_skipped_list(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            plain = "1 01-01-2024 10.00.00 to 11.00.00"
            noted = "Hyderabad trip 2 02-01-2024 10.00.00 to 10.30.00 evening"
            (root / plain).mkdir()
            (root / plain / "IMG_20240101_100000.jpg").write_bytes(b"a")
            (root / noted).mkdir()
            (root / noted / "IMG_20240102_100000.jpg").write_bytes(b"b")
            (root / "album").mkdir()
            (root / "notes.txt").write_bytes(b"x")
            model = AppModel()
            model.remember_preview(cluster_directory(root))
        folders, files = model.skipped()
        self.assertEqual(folders, (("album", SkippedReason.SUBFOLDER),))
        self.assertEqual(files, (("notes.txt", SkippedReason.NO_TIMESTAMP),))
        names = {item.name for cluster in model.result.clusters for item in cluster.files}
        self.assertEqual(names, {"IMG_20240101_100000.jpg", "IMG_20240102_100000.jpg"})
        self.assertEqual(model.status.event_folders, 2)
        self.assertTrue(model.flatten_enabled)

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
