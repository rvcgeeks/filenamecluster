"""Branches in saving, naming, and moving that the main paths do not take."""

import json
import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from filenamecluster.core import (
    Cluster,
    ClusterParams,
    FolderPreview,
    ModelOptions,
    OptionReader,
    ScanState,
    TimestampPatterns,
    TimestampedFile,
    cluster_directory,
    commit_cluster_moves,
    event_folder,
    event_folder_names,
    find_event_folder,
    folder_note,
    is_folder,
    keep_rules,
    load_model,
    locate_file,
    name_clusters,
    _overwrite,
    _params_from_options,
    _patterns_from_options,
    rule_error,
)


def _options(**changes) -> ModelOptions:
    base = dict(
        floor_hours=3,
        ceiling_hours=720,
        min_year=1990,
        max_year=2100,
        prec_clock=30,
        prec_epoch=20,
        prec_date=10,
        rules=(("clock", "Clock", "(?P<y>\\d{4})"),),
    )
    base.update(changes)
    return ModelOptions(**base)


class SaveBranchTests(unittest.TestCase):
    def test_a_broken_model_file_is_left_alone(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertIsNone(load_model(root).learned)
            (root / "filenamecluster-model.json").write_text("{", encoding="utf-8")
            keep_rules(root, [("clock", "Clock", "(", True)])
            (root / "filenamecluster-model.json").write_text(
                json.dumps({"options": [], "learned": []}), encoding="utf-8"
            )
            keep_rules(root, [("clock", "Clock", "(", True)])
            self.assertIsNone(load_model(root).options)
            self.assertIsNone(load_model(root).learned)
            (root / "filenamecluster-model.json").write_text(
                json.dumps({"options": {"rules": "no"}, "learned": {"within_hours": "bad"}}),
                encoding="utf-8",
            )
            self.assertIsNone(load_model(root).options)
            (root / "filenamecluster-model.json").write_text(
                json.dumps({"options": {"rules": ["no"]}}), encoding="utf-8"
            )
            self.assertIsNone(load_model(root).options)
            (root / "filenamecluster-model.json").write_text(
                json.dumps({"options": {"rules": []}}), encoding="utf-8"
            )
            with patch("filenamecluster.core.operations.model._write", side_effect=OSError):
                keep_rules(root, [("clock", "Clock", "(", True)])
            self.assertEqual(rule_error("Clock", "  "), "")

    def test_saved_limits_and_patterns_that_cannot_be_used_fall_back(self):
        self.assertFalse(OptionReader().accepts(_options(floor_hours=10, ceiling_hours=1)))
        self.assertEqual(_params_from_options(_options(floor_hours=10, ceiling_hours=1)).floor, ClusterParams().floor)
        broken = _options(rules=(("clock", "Clock", "("),))
        self.assertEqual(len(_patterns_from_options(broken).rules), len(TimestampPatterns().rules))

    def test_a_file_inside_an_event_folder_without_a_clock_is_skipped(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "IMG_20240101_100000.jpg").write_bytes(b"a")
            event = root / "1 01-01-2024 10.00.00 to 10.00.00"
            event.mkdir()
            (event / "notes.txt").write_bytes(b"x")
            with patch("filenamecluster.core.operations.pipeline.save_model", side_effect=OSError):
                result = cluster_directory(root)
            self.assertIn(f"{event.name}/notes.txt", result.ignored_without_timestamp)


class MoveBranchTests(unittest.TestCase):
    def test_locate_and_event_folder_refuse_unsafe_names(self):
        when = datetime(2024, 1, 1, 10, 0, 0)
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            photo = TimestampedFile("a.jpg", when)
            self.assertIsNone(event_folder(root, "missing"))
            (root / "kept").mkdir()
            self.assertEqual(event_folder(root, "kept"), root / "kept")
            self.assertIsNone(locate_file(root, TimestampedFile("a.jpg", when, source="../a.jpg"), "event"))
            self.assertIsNone(locate_file(root, photo, ""))
            self.assertIsNone(locate_file(root, photo, "bad/name"))
            self.assertIsNone(locate_file(root, TimestampedFile("a.jpg", when, source="other.jpg"), "event"))
            (root / "a.jpg").write_bytes(b"a")
            self.assertEqual(locate_file(root, photo, ""), root / "a.jpg")
            self.assertTrue(is_folder(root))
            self.assertEqual(event_folder_names(root), [])
            self.assertIsNone(folder_note("album"))
            named = name_clusters([Cluster((photo,))])
            self.assertIsNone(find_event_folder(root, named[0]))
            self.assertIsNone(locate_file(root, TimestampedFile("gone.jpg", when), named[0].name))
            placed = root / named[0].name
            placed.mkdir()
            (placed / "a.jpg").write_bytes(b"a")
            (root / "a.jpg").unlink()
            self.assertEqual(locate_file(root, photo, named[0].name), placed / "a.jpg")
            mismatch = TimestampedFile("a.jpg", when, source=f"{named[0].name}/other.jpg")
            self.assertIsNone(locate_file(root, mismatch, named[0].name))
            with patch(
                "filenamecluster.core.operations.preview.cluster_directory",
                side_effect=OSError("unreadable"),
            ):
                scan = FolderPreview().scan(root)
            self.assertIs(scan.state, ScanState.READ_ERROR)

    def test_commit_reports_a_file_that_vanished_and_replace_can_fall_back(self):
        when = datetime(2024, 1, 1, 10, 0, 0)
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            named = name_clusters([Cluster((TimestampedFile("a.jpg", when),))])
            with self.assertRaises(FileNotFoundError):
                commit_cluster_moves(root, named, ())
            source = root / "a.jpg"
            target = root / "b.jpg"
            source.write_bytes(b"new")
            target.write_bytes(b"old")
            with patch("filenamecluster.core.operations.placement.os.replace", side_effect=OSError):
                _overwrite(source, target)
            self.assertEqual(target.read_bytes(), b"new")
            self.assertFalse(source.exists())
