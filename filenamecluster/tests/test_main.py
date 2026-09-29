"""``python -m filenamecluster`` runs the window and exits with its code."""

import runpy
import unittest
from unittest.mock import patch

from filenamecluster.ui import app as app_module


class MainModuleTests(unittest.TestCase):
    def test_module_run_exits_with_the_window_code(self):
        with patch.object(app_module, "main", return_value=0) as main:
            with self.assertRaises(SystemExit) as stop:
                runpy.run_module("filenamecluster", run_name="__main__")
        main.assert_called_once_with()
        self.assertEqual(stop.exception.code, 0)
