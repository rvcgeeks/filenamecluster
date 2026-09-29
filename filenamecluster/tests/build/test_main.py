"""``python -m build`` runs the build and exits with its code."""

import runpy
import unittest
from unittest.mock import patch

from build import cli


class BuildMainModuleTests(unittest.TestCase):
    def test_module_run_exits_with_the_build_code(self):
        with patch.object(cli, "main", return_value=3) as main:
            with self.assertRaises(SystemExit) as stop:
                runpy.run_module("build", run_name="__main__")
        main.assert_called_once_with()
        self.assertEqual(stop.exception.code, 3)
