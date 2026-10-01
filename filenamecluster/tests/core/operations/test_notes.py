"""Apply keeps a folder note. Flatten still removes the folder."""

import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from filenamecluster.core.algorithm.cluster import Cluster
from filenamecluster.core.operations.notes import find_event_folder, noted_name
from filenamecluster.core.operations.organize import (
    NamedCluster,
    flatten_cluster_folders,
    move_into_cluster_folders,
    name_clusters,
)
from filenamecluster.core.operations.pipeline import cluster_directory
from filenamecluster.core.parser import TimestampedFile


def _photo(folder: Path, name: str, payload: bytes) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_bytes(payload)


class NoteTests(unittest.TestCase):
    def test_apply_keeps_a_prefix_when_the_span_grows(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "IMG_20240101_100000.jpg").write_bytes(b"a")
            (root / "IMG_20240101_110000.jpg").write_bytes(b"b")
            first = cluster_directory(root)
            created = move_into_cluster_folders(root, first.clusters)
            noted = root / f"Hyderabad trip {created[0].name}"
            created[0].rename(noted)
            (root / "IMG_20240101_113000.jpg").write_bytes(b"c")
            again = cluster_directory(root)
            self.assertEqual(len(again.clusters), 1)
            move_into_cluster_folders(root, again.clusters)
            folders = [path for path in root.iterdir() if path.is_dir()]
            self.assertEqual(len(folders), 1)
            self.assertTrue(folders[0].name.startswith("Hyderabad trip "))
            self.assertIn("11.30.00", folders[0].name)
            self.assertTrue((folders[0] / "IMG_20240101_113000.jpg").is_file())
            self.assertFalse(noted.exists())

    def test_apply_keeps_a_suffix_when_the_stamp_is_unchanged(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "IMG_20240101_100000.jpg").write_bytes(b"a")
            first = cluster_directory(root)
            created = move_into_cluster_folders(root, first.clusters)
            noted = root / f"{created[0].name} Hyderabad Trip"
            created[0].rename(noted)
            again = cluster_directory(root)
            move_into_cluster_folders(root, again.clusters)
            self.assertTrue(noted.is_dir())
            self.assertTrue((noted / "IMG_20240101_100000.jpg").is_file())
            self.assertFalse((root / again.clusters[0].name).exists())

    def test_the_note_on_the_fuller_folder_wins_when_events_merge(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _photo(root / "Trip A 1 01-01-2024 10.00.00 to 10.30.00", "IMG_20240101_100000.jpg", b"a")
            _photo(root / "Trip A 1 01-01-2024 10.00.00 to 10.30.00", "IMG_20240101_103000.jpg", b"b")
            _photo(root / "Trip B 2 01-01-2024 10.40.00 to 10.50.00", "IMG_20240101_104000.jpg", b"c")
            result = cluster_directory(root)
            self.assertEqual(len(result.clusters), 1)
            move_into_cluster_folders(root, result.clusters)
            folders = [path.name for path in root.iterdir() if path.is_dir()]
            self.assertEqual(folders, [f"Trip A {result.clusters[0].name}"])
            self.assertEqual(flatten_cluster_folders(root), 3)
            self.assertFalse(any(path.is_dir() for path in root.iterdir()))

    def test_a_note_on_both_sides_is_kept(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            stamp = "1 01-01-2024 10.00.00 to 11.00.00"
            _photo(root / f"Goa {stamp} evening", "IMG_20240101_100000.jpg", b"a")
            _photo(root / f"Goa {stamp} evening", "IMG_20240101_110000.jpg", b"b")
            result = cluster_directory(root)
            self.assertEqual(noted_name(root, result.clusters[0]), f"Goa {result.clusters[0].name} evening")
            move_into_cluster_folders(root, result.clusters)
            self.assertTrue((root / f"Goa {result.clusters[0].name} evening").is_dir())

    def test_finds_a_noted_folder_when_the_preview_still_uses_the_stamp(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            when = datetime(2024, 1, 1, 10, 0, 0)
            cluster = name_clusters([Cluster((TimestampedFile("a.jpg", when),))])[0]
            folder = root / f"Hyderabad trip {cluster.name}"
            folder.mkdir()
            found = find_event_folder(root, cluster)
            self.assertEqual(found, folder)
            self.assertIsNone(find_event_folder(root / "missing", cluster))
            self.assertEqual(noted_name(root, cluster), cluster.name)

    def test_opens_the_folder_that_holds_the_files(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            when = datetime(2024, 1, 1, 10, 0, 0)
            later = datetime(2024, 1, 1, 11, 0, 0)
            placed = "Hyderabad trip 1 01-01-2024 10.00.00 to 11.00.00"
            (root / placed).mkdir()
            cluster = NamedCluster(
                4,
                "4 01-01-2024 10.00.00 to 12.00.00",
                (
                    TimestampedFile("a.jpg", when, source=f"{placed}/a.jpg"),
                    TimestampedFile("b.jpg", later),
                ),
            )
            self.assertEqual(find_event_folder(root, cluster), root / placed)
            self.assertEqual(noted_name(root, cluster), f"Hyderabad trip {cluster.name}")

    def test_ignores_a_plain_folder_and_a_stamp_with_no_note(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            when = datetime(2024, 1, 1, 10, 0, 0)
            cluster = name_clusters([Cluster((TimestampedFile("a.jpg", when),))])[0]
            plain = root / cluster.name
            plain.mkdir()
            (root / "notes.txt").write_bytes(b"x")
            self.assertEqual(find_event_folder(root, cluster), plain)
            placed = NamedCluster(
                1,
                cluster.name,
                (
                    TimestampedFile("a.jpg", when, source=f"{cluster.name}/a.jpg"),
                    TimestampedFile("b.jpg", when, source="album/b.jpg"),
                ),
            )
            self.assertEqual(noted_name(root, placed), cluster.name)
            plain.rename(root / "album")
            self.assertIsNone(find_event_folder(root, cluster))
