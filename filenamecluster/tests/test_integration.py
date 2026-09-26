"""Cluster a folder holding every name from the real camera roll."""

import re
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from filenamecluster.core.organize import cluster_name, move_into_cluster_folders
from filenamecluster.core.parse import parse_timestamp
from filenamecluster.core.pipeline import cluster_directory

LISTING = Path(__file__).resolve().parents[2] / "workspace" / "filenames.txt"
DIR_ROW = re.compile(r"^\d{2}-\d{2}-\d{4}\s+\d{2}:\d{2}\s+(<DIR>|[\d,]+)\s+(.*\S)\s*$")
SAME_DAY = re.compile(
    r"^\d+ \d{2}-\d{2}-\d{4} \d{2}\.\d{2}\.\d{2} to \d{2}\.\d{2}\.\d{2}$"
)
MULTI_DAY = re.compile(
    r"^\d+ \d{2}-\d{2}-\d{4} \d{2}\.\d{2}\.\d{2} to "
    r"\d{2}-\d{2}-\d{4} \d{2}\.\d{2}\.\d{2}$"
)


def camera_roll_names() -> tuple[list[str], list[str]]:
    files: list[str] = []
    folders: list[str] = []
    for line in LISTING.read_text(encoding="utf-8-sig").splitlines():
        match = DIR_ROW.match(line)
        if match is None:
            continue
        kind, name = match.groups()
        if kind != "<DIR>":
            files.append(name)
        elif name not in {".", ".."}:
            folders.append(name)
    return files, folders


class CameraRollTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not LISTING.is_file():
            raise unittest.SkipTest("workspace/filenames.txt is missing")
        cls.tmp = TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        cls.files, cls.folders = camera_roll_names()
        for name in cls.files:
            (cls.root / name).touch()
        for name in cls.folders:
            (cls.root / name).mkdir()
        cls.result = cluster_directory(cls.root)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_folders_and_undated_names_are_left_out(self):
        clustered = {item.name for cluster in self.result.clusters for item in cluster.files}
        undated = {name for name in self.files if parse_timestamp(name) is None}
        self.assertEqual(set(self.result.ignored_without_timestamp), undated)
        self.assertEqual(clustered, set(self.files) - undated)
        self.assertEqual(set(self.result.ignored_directories), set(self.folders))
        self.assertIn("a", self.folders)
        self.assertIn("DaSr70bB1F3XK9Kf8Q0040Q8.jpg", undated)
        self.assertIn(".escheck.tmp", undated)
        self.assertIn("06be3c8e9fbd4c67954114367c696add.mp4", undated)
        self.assertIn("20200101_001000.mp4", clustered)
        self.assertIn("img1462863402727.jpg", clustered)
        self.assertIn("CamScanner 11-21-2024 12.22.jpg", clustered)
        self.assertGreater(len(clustered), 9000)
        self.assertLess(len(undated), 30)

    def test_clusters_are_chronological_events(self):
        params = self.result.params
        self.assertGreaterEqual(len(self.result.clusters), 2)
        for previous, cluster in zip(self.result.clusters, self.result.clusters[1:]):
            self.assertGreater(cluster.start - previous.end, params.floor)
        for index, cluster in enumerate(self.result.clusters, start=1):
            self.assertEqual(cluster.number, index)
            self.assertEqual(cluster.name, cluster_name(index, cluster.start, cluster.end))
            if cluster.start.date() == cluster.end.date():
                self.assertRegex(cluster.name, SAME_DAY)
            else:
                self.assertRegex(cluster.name, MULTI_DAY)
            for earlier, later in zip(cluster.files, cluster.files[1:]):
                self.assertGreaterEqual(later.timestamp, earlier.timestamp)
                self.assertLessEqual(later.timestamp - earlier.timestamp, params.ceiling)

    def test_zz_moving_leaves_only_undated_files_loose(self):
        move_into_cluster_folders(self.root, self.result.clusters)
        loose = sorted(
            path.name
            for path in self.root.iterdir()
            if path.is_file() and path.name != "filenamecluster-model.json"
        )
        self.assertEqual(loose, sorted(self.result.ignored_without_timestamp))
        self.assertTrue((self.root / "filenamecluster-model.json").is_file())
        again = cluster_directory(self.root)
        again_names = [[item.name for item in cluster.files] for cluster in again.clusters]
        first_names = [[item.name for item in cluster.files] for cluster in self.result.clusters]
        self.assertEqual(again_names, first_names)
        self.assertEqual(
            set(again.ignored_directories),
            set(self.folders) | {cluster.name for cluster in self.result.clusters},
        )


if __name__ == "__main__":
    unittest.main()
