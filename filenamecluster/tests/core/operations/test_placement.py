"""Placement plans name clashes and then replaces or skips them."""

import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from filenamecluster.core import (
    Cluster,
    TimestampedFile,
    flatten_cluster_folders,
    move_into_cluster_folders,
    name_clusters,
    plan_cluster_moves,
    plan_flatten_moves,
)


def named(name: str, when: datetime):
    return name_clusters([Cluster((TimestampedFile(name, when),))])


class PlacementTests(unittest.TestCase):
    def test_replace_overwrites_and_skip_leaves_both_files(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.jpg").write_bytes(b"new")
            clusters = named("a.jpg", datetime(2024, 1, 1, 10, 0, 0))
            folder = root / clusters[0].name
            folder.mkdir()
            (folder / "a.jpg").write_bytes(b"old")

            plan = plan_cluster_moves(root, clusters)
            self.assertEqual(len(plan.clashes), 1)
            self.assertEqual(plan.clashes[0].target.name, "a.jpg")
            self.assertEqual(plan.moves, ())

            move_into_cluster_folders(root, clusters, replacing=())
            self.assertEqual((root / "a.jpg").read_bytes(), b"new")
            self.assertEqual((folder / "a.jpg").read_bytes(), b"old")

            move_into_cluster_folders(root, clusters, replacing=[plan.clashes[0].source])
            self.assertFalse((root / "a.jpg").exists())
            self.assertEqual((folder / "a.jpg").read_bytes(), b"new")

    def test_a_free_file_moves_while_a_clash_is_skipped(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.jpg").write_bytes(b"a")
            (root / "b.jpg").write_bytes(b"b")
            clusters = name_clusters(
                [
                    Cluster(
                        (
                            TimestampedFile("a.jpg", datetime(2024, 1, 1, 10, 0, 0)),
                            TimestampedFile("b.jpg", datetime(2024, 1, 1, 11, 0, 0)),
                        )
                    )
                ]
            )
            folder = root / clusters[0].name
            folder.mkdir()
            (folder / "a.jpg").write_bytes(b"keep")
            move_into_cluster_folders(root, clusters, replacing=())
            self.assertEqual((folder / "a.jpg").read_bytes(), b"keep")
            self.assertEqual((folder / "b.jpg").read_bytes(), b"b")
            self.assertTrue((root / "a.jpg").is_file())
            self.assertFalse((root / "b.jpg").exists())

    def test_flatten_replace_and_skip(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "IMG_20240101_100000.jpg").write_bytes(b"inside")
            (root / "IMG_20240108_090000.jpg").write_bytes(b"other")
            from filenamecluster.core import cluster_directory

            result = cluster_directory(root)
            move_into_cluster_folders(root, result.clusters)
            (root / "IMG_20240101_100000.jpg").write_bytes(b"outside")
            kept = next(
                path
                for path in root.rglob("IMG_20240101_100000.jpg")
                if path.parent != root
            )
            plan = plan_flatten_moves(root)
            self.assertEqual([item.target.name for item in plan.clashes], ["IMG_20240101_100000.jpg"])
            self.assertEqual(len(plan.moves), 1)

            self.assertEqual(flatten_cluster_folders(root, replacing=()), 1)
            self.assertEqual((root / "IMG_20240101_100000.jpg").read_bytes(), b"outside")
            self.assertEqual(kept.read_bytes(), b"inside")
            self.assertEqual((root / "IMG_20240108_090000.jpg").read_bytes(), b"other")

            flatten_cluster_folders(root, replacing=[kept])
            self.assertEqual((root / "IMG_20240101_100000.jpg").read_bytes(), b"inside")
            self.assertFalse(kept.exists())
            self.assertFalse(kept.parent.exists())

    def test_a_prepared_flatten_plan_is_not_built_again(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "IMG_20240101_100000.jpg").write_bytes(b"inside")
            from filenamecluster.core import cluster_directory

            result = cluster_directory(root)
            move_into_cluster_folders(root, result.clusters)
            plan = plan_flatten_moves(root)
            with patch("filenamecluster.core.operations.placement.plan_flatten_moves") as again:
                self.assertEqual(flatten_cluster_folders(root, plan=plan), 1)
            again.assert_not_called()
            self.assertTrue((root / "IMG_20240101_100000.jpg").is_file())
