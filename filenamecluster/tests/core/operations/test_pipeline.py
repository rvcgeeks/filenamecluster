"""Scan a folder, cluster it, and keep a later batch in the same series."""

import re
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from filenamecluster.core import (
    ClusterParams,
    cluster_directory,
    cluster_name,
    move_into_cluster_folders,
    parse_timestamp,
)


LISTING = Path(__file__).resolve().parents[4] / "workspace" / "filenames.txt"
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


class PipelineTests(unittest.TestCase):
    def test_folder_is_clustered_and_skipped_names_are_kept(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in (
                "IMG_20240101_100000.jpg",
                "IMG_20240101_110000.jpg",
                "IMG_20240108_090000.jpg",
                "notes.txt",
            ):
                (root / name).write_bytes(b"x")
            (root / "album").mkdir()
            result = cluster_directory(root)
            self.assertEqual([cluster.number for cluster in result.clusters], [1, 2])
            self.assertEqual(len(result.clusters[0].files), 2)
            self.assertEqual(result.file_count, 3)
            self.assertEqual(result.ignored_without_timestamp, ("notes.txt",))
            self.assertEqual(result.ignored_directories, ("album",))
            self.assertEqual(result.params, ClusterParams())

    def test_new_photos_join_an_event_or_start_another(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in (
                "IMG_20240101_100000.jpg",
                "IMG_20240101_110000.jpg",
                "IMG_20240110_100000.jpg",
            ):
                (root / name).write_bytes(b"x")
            first = cluster_directory(root)
            self.assertEqual([len(cluster.files) for cluster in first.clusters], [2, 1])
            move_into_cluster_folders(root, first.clusters)

            (root / "IMG_20240101_113000.jpg").write_bytes(b"joined")
            (root / "IMG_20240220_100000.jpg").write_bytes(b"later")
            again = cluster_directory(root)
            self.assertEqual([len(cluster.files) for cluster in again.clusters], [3, 1, 1])
            self.assertEqual(
                [item.name for item in again.clusters[0].files],
                [
                    "IMG_20240101_100000.jpg",
                    "IMG_20240101_110000.jpg",
                    "IMG_20240101_113000.jpg",
                ],
            )
            self.assertEqual(again.clusters[2].files[0].name, "IMG_20240220_100000.jpg")

            move_into_cluster_folders(root, again.clusters)
            loose = sorted(
                path.name
                for path in root.iterdir()
                if path.is_file() and path.name != "filenamecluster-model.json"
            )
            self.assertEqual(loose, [])
            self.assertEqual(
                (root / again.clusters[0].name / "IMG_20240101_113000.jpg").read_bytes(),
                b"joined",
            )
            self.assertTrue((root / again.clusters[2].name / "IMG_20240220_100000.jpg").is_file())
            self.assertFalse((root / first.clusters[0].name).exists())

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
        self.assertEqual(len(self.files), 11484)
        self.assertEqual(len(undated), 15)
        self.assertIn("BeautyPlus_20160406180905_save.jpg", clustered)
        self.assertIn("20200101_001000.mp4", clustered)
        self.assertIn("img1462863402727.jpg", clustered)
        self.assertIn("CamScanner 11-21-2024 12.22.jpg", clustered)
        self.assertIn("IMG_20200317_150503_BURST1.jpg", clustered)
        self.assertIn("VID_20201116_172025_HSR_120.mp4", clustered)
        self.assertIn("VID_20210401_142601_exported_16951.jpg", clustered)
        self.assertIn("IMG_20210526_214754_HHT.jpg", clustered)
        self.assertIn("Screenshot_2019-08-14-09-26-13-264_lockscreen.png", clustered)
        self.assertIn("PhotoGrid_1581064265269.jpg", clustered)
        self.assertIn("IMG-20170610-WA0005.jpg", clustered)
        self.assertIn("VID-20231230-WA0013.mp4", clustered)
        self.assertIn("InShot_20240127_220124404.mp4", clustered)
        self.assertIn("Project_12_02_2023-12-03-01-32-06.mp4", clustered)
        self.assertEqual(len(clustered), 11469)

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

