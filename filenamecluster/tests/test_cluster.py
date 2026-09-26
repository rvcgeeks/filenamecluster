"""Timestamp-gap clustering, learned per folder, with safety limits and corrections."""

import math
import unittest
from datetime import datetime, timedelta

from filenamecluster.core.cluster import ClusterParams, cluster_files
from filenamecluster.core.learn import fit_gap_model
from filenamecluster.core.model_file import FolderModel
from filenamecluster.core.parse import TimestampedFile


def files_at(*points: datetime) -> list[TimestampedFile]:
    return [TimestampedFile(f"shot-{index}.jpg", point) for index, point in enumerate(points)]


def burst(start: datetime, count: int, step: timedelta = timedelta(minutes=5)) -> list[datetime]:
    return [start + step * index for index in range(count)]


class ClusterParamsTests(unittest.TestCase):
    def test_defaults_are_wide_safety_limits(self):
        params = ClusterParams()
        self.assertEqual(params.floor, timedelta(hours=3))
        self.assertEqual(params.ceiling, timedelta(days=30))

    def test_rejects_impossible_bounds(self):
        with self.assertRaises(ValueError):
            ClusterParams(floor=timedelta(0))
        with self.assertRaises(ValueError):
            ClusterParams(floor=timedelta(hours=10), ceiling=timedelta(hours=10))


class LearnTests(unittest.TestCase):
    def test_two_patterns_meet_between_their_centers(self):
        short = [math.log(hours) for hours in (0.2, 0.3, 0.5, 1, 2, 3)]
        long = [math.log(hours) for hours in (40, 50, 70, 90, 120)]
        model = fit_gap_model(short + long)
        self.assertIsNotNone(model)
        assert model is not None
        self.assertTrue(model.separated)
        self.assertLess(model.within_hours, model.boundary_hours)
        self.assertLess(model.boundary_hours, model.between_hours)
        self.assertFalse(model.splits(2, 3, 24 * 30))
        self.assertTrue(model.splits(80, 3, 24 * 30))

    def test_too_few_gaps_are_not_a_model(self):
        self.assertIsNone(fit_gap_model([0.0, 1.0, 2.0]))


class ClusterFilesTests(unittest.TestCase):
    def test_empty_and_single_file(self):
        clusters, model = cluster_files([])
        self.assertEqual(clusters, [])
        self.assertIsNone(model)
        only = TimestampedFile("only.jpg", datetime(2024, 1, 1, 10, 0, 0))
        clusters, model = cluster_files([only])
        self.assertEqual(clusters[0].files, (only,))
        self.assertIsNone(model)

    def test_sorts_by_time_then_name(self):
        later = TimestampedFile("b.jpg", datetime(2024, 1, 1, 12, 0, 0))
        early_b = TimestampedFile("b.jpg", datetime(2024, 1, 1, 10, 0, 0))
        early_a = TimestampedFile("a.jpg", datetime(2024, 1, 1, 10, 0, 0))
        clusters, _ = cluster_files([later, early_b, early_a])
        self.assertEqual([item.name for item in clusters[0].files], ["a.jpg", "b.jpg", "b.jpg"])

    def test_floor_keeps_a_short_pause_together(self):
        start = datetime(2024, 8, 12, 22, 0, 0)
        clusters, _ = cluster_files(files_at(start, start + timedelta(hours=2)))
        self.assertEqual(len(clusters), 1)

    def test_ceiling_always_splits(self):
        start = datetime(2024, 1, 1, 10, 0, 0)
        clusters, _ = cluster_files(files_at(start, start + timedelta(days=31)))
        self.assertEqual(len(clusters), 2)

    def test_a_frequent_photographer_and_a_quiet_one_learn_different_boundaries(self):
        start = datetime(2024, 6, 1, 9, 0, 0)
        trip = timedelta(days=20)
        vlogger = [start + timedelta(hours=4 * step) for step in range(12)] + [
            start + trip + timedelta(hours=4 * step) for step in range(12)
        ]
        vlogger_clusters, vlogger_model = cluster_files(files_at(*vlogger))
        self.assertIsNotNone(vlogger_model)
        assert vlogger_model is not None
        self.assertEqual(len(vlogger_clusters), 2)
        self.assertLess(vlogger_model.boundary_hours, 24 * 10)

        quiet: list[datetime] = []
        cursor = start
        for _ in range(10):
            quiet.append(cursor)
            cursor += timedelta(days=6)
        for _ in range(6):
            quiet.append(cursor)
            cursor += timedelta(days=20)
        quiet_clusters, quiet_model = cluster_files(files_at(*quiet))
        self.assertGreater(len(quiet_clusters), 1)
        self.assertIsNotNone(quiet_model)
        assert quiet_model is not None
        self.assertTrue(quiet_model.separated)
        self.assertGreater(quiet_model.boundary_hours, vlogger_model.boundary_hours)

    def test_repeated_multi_day_pauses_do_not_chain_into_one_event(self):
        start = datetime(2021, 5, 14, 12, 0, 0)
        points: list[datetime] = []
        for day in (0, 5, 9, 16, 20, 28, 34, 40, 46):
            points.extend(burst(start + timedelta(days=day), 12))
        clusters, model = cluster_files(files_at(*points))
        self.assertIsNotNone(model)
        self.assertGreaterEqual(len(clusters), 4)
        self.assertTrue(all(cluster.end - cluster.start < timedelta(days=10) for cluster in clusters))

    def test_a_saved_boundary_is_kept_when_too_few_pauses_remain(self):
        from filenamecluster.core.learn import GapModel

        start = datetime(2024, 1, 1, 10, 0, 0)
        photos = files_at(start, start + timedelta(hours=10))
        clusters, model = cluster_files(photos)
        self.assertIsNone(model)
        self.assertEqual(len(clusters), 1)

        saved = FolderModel(
            learned=GapModel(
                within_hours=2,
                between_hours=48,
                boundary_hours=5,
                separated=True,
            )
        )
        clusters, model = cluster_files(photos, model=saved)
        self.assertEqual(len(clusters), 2)
        self.assertIsNotNone(model)
        assert model is not None
        self.assertEqual(model.boundary_hours, 5)

    def test_saved_model_keeps_full_float_precision(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path

        from filenamecluster.core.learn import GapModel
        from filenamecluster.core.model_file import load_model, save_model

        learned = GapModel(
            within_hours=math.pi,
            between_hours=math.tau,
            boundary_hours=math.sqrt(2),
            separated=True,
        )
        with TemporaryDirectory() as tmp:
            path = save_model(Path(tmp), FolderModel(learned=learned))
            text = path.read_text(encoding="utf-8")
            self.assertIn(repr(math.pi), text)
            self.assertEqual(load_model(path.parent).learned, learned)

    def test_tiny_folder_uses_the_day_and_a_half_fallback(self):
        start = datetime(2024, 1, 1, 10, 0, 0)
        clusters, model = cluster_files(
            files_at(start, start + timedelta(hours=1), start + timedelta(days=8))
        )
        self.assertIsNone(model)
        self.assertEqual(len(clusters), 2)
        self.assertEqual(len(clusters[0].files), 2)


if __name__ == "__main__":
    unittest.main()
