"""The build reads the package beside ``pyproject.toml`` and writes ``dist/``."""

import unittest

from build import paths


class PathTests(unittest.TestCase):
    def test_paths_point_at_the_project(self):
        self.assertTrue((paths.ROOT / "pyproject.toml").is_file())
        self.assertTrue((paths.PACKAGE / "__main__.py").is_file())
        self.assertTrue((paths.ASSETS / "icon.png").is_file())
        self.assertEqual(paths.DIST, paths.ROOT / "dist")
        self.assertEqual(paths.MAC_APP, paths.DIST / "filenamecluster.app")
