"""The learned boundary, and the options stored beside it."""

import json
import math
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from filenamecluster.core.cluster import ClusterParams
from filenamecluster.core.learn import FolderModel, fit_gap_model

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

class SavedOptionsTests(unittest.TestCase):
    def test_options_round_trip_beside_learned_without_changing_the_boundary(self):
        from filenamecluster.core.learn import GapModel, ModelOptions, load_model, save_model
        from filenamecluster.core.parse import TimestampPatterns

        patterns = TimestampPatterns()
        options = ModelOptions(
            floor_hours=2,
            ceiling_hours=3,
            min_year=1990,
            max_year=2100,
            prec_clock=30,
            prec_epoch=20,
            prec_date=10,
            rules=tuple((rule.key, rule.description, rule.pattern) for rule in patterns.rules),
        )
        learned = GapModel(within_hours=1.5, between_hours=40, boundary_hours=8, separated=True)
        kept = FolderModel(learned=learned, options=options).with_learned(learned)
        self.assertEqual(kept.learned, learned)
        self.assertEqual(kept.options, options)
        self.assertEqual(kept.with_options(None).learned, learned)
        self.assertIsNone(kept.with_options(None).options)

        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            save_model(folder, FolderModel(learned=learned, options=options))
            raw = json.loads((folder / "filenamecluster-model.json").read_text(encoding="utf-8"))
            self.assertEqual(set(raw), {"learned", "options"})
            self.assertEqual(raw["learned"]["boundary_hours"], learned.boundary_hours)
            self.assertEqual(raw["options"]["floor_hours"], 2)
            loaded = load_model(folder)
            self.assertEqual(loaded.learned, learned)
            self.assertEqual(loaded.options, options)

            raw["options"] = {"floor_hours": "bad"}
            (folder / "filenamecluster-model.json").write_text(json.dumps(raw), encoding="utf-8")
            broken = load_model(folder)
            self.assertEqual(broken.learned, learned)
            self.assertIsNone(broken.options)

            (folder / "filenamecluster-model.json").write_text(
                json.dumps({"learned": raw["learned"]}), encoding="utf-8"
            )
            legacy = load_model(folder)
            self.assertEqual(legacy.learned, learned)
            self.assertIsNone(legacy.options)

    def test_saved_options_override_defaults_until_the_caller_passes_params(self):
        from filenamecluster.core.learn import ModelOptions, load_model, save_model
        from filenamecluster.core.parse import TimestampPatterns
        from filenamecluster.core.pipeline import cluster_directory

        patterns = TimestampPatterns()
        options = ModelOptions(
            floor_hours=2,
            ceiling_hours=3,
            min_year=patterns.min_year,
            max_year=patterns.max_year,
            prec_clock=patterns.prec_clock,
            prec_epoch=patterns.prec_epoch,
            prec_date=patterns.prec_date,
            rules=tuple((rule.key, rule.description, rule.pattern) for rule in patterns.rules),
        )
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            for name in (
                "IMG_20240101_100000.jpg",
                "IMG_20240101_110000.jpg",
                "IMG_20240102_090000.jpg",
                "IMG_20240120_080000.jpg",
            ):
                (folder / name).write_bytes(b"x")
            save_model(folder, FolderModel(options=options))
            overridden = cluster_directory(folder)
            self.assertEqual(overridden.params.floor_hours, 2)
            self.assertEqual(overridden.params.ceiling_hours, 3)
            self.assertEqual(len(overridden.clusters), 3)
            explicit = cluster_directory(folder, ClusterParams())
            self.assertEqual(explicit.params.floor_hours, 3)
            self.assertEqual(load_model(folder).options.floor_hours, 3)
            self.assertEqual(load_model(folder).learned, explicit.model)

