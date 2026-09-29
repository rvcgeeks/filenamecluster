"""The model file: learned boundary and saved options."""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from filenamecluster.core.algorithm import ClusterParams, FolderModel

class SavedOptionsTests(unittest.TestCase):
    def test_options_round_trip_beside_learned_without_changing_the_boundary(self):
        from filenamecluster.core.algorithm import GapModel, ModelOptions
        from filenamecluster.core.operations import load_model, save_model
        from filenamecluster.core.parser import TimestampPatterns

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
        from filenamecluster.core.algorithm import ModelOptions
        from filenamecluster.core.operations import load_model, save_model
        from filenamecluster.core.parser import TimestampPatterns
        from filenamecluster.core.operations.pipeline import cluster_directory

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
