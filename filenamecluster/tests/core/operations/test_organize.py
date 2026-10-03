"""Cluster names, clustering a folder, and moving files into folders."""

import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from filenamecluster.core import (
    Cluster,
    TimestampedFile,
    cluster_directory,
    cluster_name,
    flatten_cluster_folders,
    is_cluster_folder_name,
    move_into_cluster_folders,
    name_clusters,
)


def stamp(name: str, when: datetime) -> TimestampedFile:
    return TimestampedFile(name, when)

class ClusterNameTests(unittest.TestCase):
    def test_multi_day_and_same_day_examples(self):
        self.assertEqual(
            cluster_name(
                1,
                datetime(2026, 8, 12, 22, 34, 11),
                datetime(2026, 8, 17, 2, 56, 23),
            ),
            "1 12-08-2026 22.34.11 to 17-08-2026 02.56.23",
        )
        self.assertEqual(
            cluster_name(
                2,
                datetime(2026, 8, 23, 12, 45, 22),
                datetime(2026, 9, 3, 23, 34, 12),
            ),
            "2 23-08-2026 12.45.22 to 03-09-2026 23.34.12",
        )
        self.assertEqual(
            cluster_name(
                3,
                datetime(2026, 8, 12, 22, 34, 11),
                datetime(2026, 8, 12, 23, 10, 0),
            ),
            "3 12-08-2026 22.34.11 to 23.10.00",
        )

    def test_number_must_be_positive(self):
        when = datetime(2024, 1, 1, 10, 0, 0)
        with self.assertRaises(ValueError):
            cluster_name(0, when, when)

    def test_names_follow_chronological_cluster_order(self):
        first = Cluster(
            (
                stamp("a.jpg", datetime(2024, 1, 1, 10, 0, 0)),
                stamp("b.jpg", datetime(2024, 1, 1, 12, 0, 0)),
            )
        )
        second = Cluster((stamp("c.jpg", datetime(2024, 1, 3, 9, 0, 0)),))
        named = name_clusters([first, second])
        self.assertEqual([item.number for item in named], [1, 2])
        self.assertTrue(named[0].name.startswith("1 01-01-2024 "))
        self.assertTrue(named[1].name.startswith("2 03-01-2024 "))
        self.assertEqual(named[1].start, datetime(2024, 1, 3, 9, 0, 0))
        self.assertEqual(named[1].end, named[1].start)

class MoveTests(unittest.TestCase):
    def test_input_folder_files_move_into_storage(self):
        with TemporaryDirectory() as tmp:
            storage = Path(tmp) / "storage"
            incoming = Path(tmp) / "camera"
            storage.mkdir()
            incoming.mkdir()
            (incoming / "IMG_20240101_100000.jpg").write_bytes(b"from-input")
            result = cluster_directory(storage, source=incoming)
            self.assertEqual(result.file_count, 1)
            self.assertEqual(result.clusters[0].files[0].origin, "input")
            created = move_into_cluster_folders(storage, result.clusters, source=incoming)
            placed = created[0] / "IMG_20240101_100000.jpg"
            self.assertEqual(placed.read_bytes(), b"from-input")
            self.assertFalse((incoming / "IMG_20240101_100000.jpg").exists())
            self.assertTrue((storage / "filenamecluster-model.json").is_file())

    def test_moves_files_into_named_folders(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "IMG_20240101_100000.jpg").write_bytes(b"a")
            (root / "IMG_20240101_110000.jpg").write_bytes(b"b")
            (root / "notes.txt").write_bytes(b"keep")
            result = cluster_directory(root)
            created = move_into_cluster_folders(root, result.clusters)
            self.assertEqual(len(created), 1)
            self.assertTrue((created[0] / "IMG_20240101_100000.jpg").is_file())
            self.assertTrue((created[0] / "IMG_20240101_110000.jpg").is_file())
            self.assertFalse((root / "IMG_20240101_100000.jpg").exists())
            self.assertTrue((root / "notes.txt").is_file())

    def test_rejects_unsafe_missing_and_existing_destinations(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            photo = stamp("a.jpg", datetime(2024, 1, 1, 10, 0, 0))
            named = name_clusters([Cluster((photo,))])
            with self.assertRaises(FileNotFoundError):
                move_into_cluster_folders(root, named)

            self.assertFalse((root / named[0].name).exists())

            (root / "a.jpg").write_bytes(b"a")
            folder = root / named[0].name
            folder.mkdir()
            (folder / "a.jpg").write_bytes(b"already")
            with self.assertRaises(FileExistsError):
                move_into_cluster_folders(root, named)
            self.assertEqual((root / "a.jpg").read_bytes(), b"a")
            self.assertEqual((folder / "a.jpg").read_bytes(), b"already")

            unsafe = name_clusters(
                [Cluster((stamp("../a.jpg", datetime(2024, 1, 1, 10, 0, 0)),))]
            )
            with self.assertRaises(ValueError):
                move_into_cluster_folders(root, unsafe)

            nested = name_clusters(
                [Cluster((stamp("dir/a.jpg", datetime(2024, 1, 1, 10, 0, 0)),))]
            )
            with self.assertRaises(ValueError):
                move_into_cluster_folders(root, nested)

            blank = name_clusters(
                [Cluster((stamp("", datetime(2024, 1, 1, 10, 0, 0)),))]
            )
            with self.assertRaises(ValueError):
                move_into_cluster_folders(root, blank)

        with self.assertRaises(NotADirectoryError):
            move_into_cluster_folders(Path(tmp) / "missing", named)

class FlattenTests(unittest.TestCase):
    def test_moves_files_back_and_removes_event_folders(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "IMG_20240101_100000.jpg").write_bytes(b"a")
            (root / "IMG_20240101_110000.jpg").write_bytes(b"b")
            (root / "notes.txt").write_bytes(b"keep")
            (root / "album").mkdir()
            (root / "album" / "keep.jpg").write_bytes(b"c")
            result = cluster_directory(root)
            move_into_cluster_folders(root, result.clusters)
            self.assertFalse(is_cluster_folder_name("album"))
            self.assertTrue(is_cluster_folder_name(result.clusters[0].name))

            moved = flatten_cluster_folders(root)
            self.assertEqual(moved, 2)
            self.assertEqual((root / "IMG_20240101_100000.jpg").read_bytes(), b"a")
            self.assertTrue((root / "IMG_20240101_110000.jpg").is_file())
            self.assertTrue((root / "notes.txt").is_file())
            self.assertTrue((root / "album" / "keep.jpg").is_file())
            self.assertFalse((root / result.clusters[0].name).exists())

    def test_stops_before_moving_when_a_name_is_already_there(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "IMG_20240101_100000.jpg").write_bytes(b"loose")
            (root / "IMG_20240108_090000.jpg").write_bytes(b"later")
            result = cluster_directory(root)
            move_into_cluster_folders(root, result.clusters)
            (root / "IMG_20240101_100000.jpg").write_bytes(b"loose")
            with self.assertRaises(FileExistsError):
                flatten_cluster_folders(root)
            self.assertFalse((root / "IMG_20240108_090000.jpg").is_file())
            self.assertTrue(
                (root / result.clusters[1].name / "IMG_20240108_090000.jpg").is_file()
            )

    def test_keeps_an_event_folder_that_still_holds_a_subfolder(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "IMG_20240101_100000.jpg").write_bytes(b"a")
            result = cluster_directory(root)
            created = move_into_cluster_folders(root, result.clusters)
            (created[0] / "nested").mkdir()
            self.assertEqual(flatten_cluster_folders(root), 1)
            self.assertTrue((root / "IMG_20240101_100000.jpg").is_file())
            self.assertTrue((created[0] / "nested").is_dir())

    def test_rejects_a_file_path(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "notes.txt"
            path.write_bytes(b"x")
            with self.assertRaises(NotADirectoryError):
                flatten_cluster_folders(path)

