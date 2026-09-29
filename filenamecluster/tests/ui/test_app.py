"""Build the window and start the Tk loop."""

import unittest
from unittest.mock import patch

from filenamecluster.log import log_path
from filenamecluster.ui import app as app_module
from conftest import WindowCase, make_root


class AppTests(WindowCase):
    def test_starts_empty_with_apply_disabled(self):
        self.app.controller.refresh()
        self.assertIn("disabled", self.app.view.apply_button.state())
        self.assertIn("disabled", self.app.view.flatten_button.state())
        self.assertIsNone(self.app.view.overview.scale)
        about = self.app.view.about_text.get("1.0", "end")
        self.assertIn("Apply clustering", about)
        self.assertIn("Flatten clustering", about)
        self.assertIn("filenamecluster-model.json", about)
        self.assertIn("timestamps only", about)
        self.assertIn("1990 and 2100", about)
        self.assertIn("Filename patterns", about)
        self.assertIn("(?P<y>", about)
        self.assertIn("finditer", about)
        self.assertIn("pid=", about)
        self.assertIn(str(log_path()), about)


class MainTests(unittest.TestCase):
    def test_main_builds_the_app_and_runs_the_loop(self):
        root = make_root()
        with (
            patch.object(app_module.tk, "Tk", return_value=root),
            patch.object(root, "mainloop") as loop,
        ):
            self.assertEqual(app_module.main(), 0)
        loop.assert_called_once()
        self.assertEqual(root.state(), "withdrawn")
        root.destroy()
