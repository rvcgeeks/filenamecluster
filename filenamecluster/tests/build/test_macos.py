"""enable_retina: the Mac app declares high-resolution drawing."""

import plistlib
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from build.macos import enable_retina


class RetinaTests(unittest.TestCase):
    def test_the_app_plist_gains_high_resolution(self):
        with TemporaryDirectory() as folder:
            app = Path(folder) / "filenamecluster.app"
            plist = app / "Contents" / "Info.plist"
            plist.parent.mkdir(parents=True)
            plist.write_bytes(plistlib.dumps({"CFBundleName": "filenamecluster"}))
            self.assertTrue(enable_retina(app))
            info = plistlib.loads(plist.read_bytes())
        self.assertIs(info["NSHighResolutionCapable"], True)
        self.assertEqual(info["CFBundleName"], "filenamecluster")

    def test_a_missing_app_is_left_alone(self):
        with TemporaryDirectory() as folder:
            self.assertFalse(enable_retina(Path(folder) / "missing.app"))
