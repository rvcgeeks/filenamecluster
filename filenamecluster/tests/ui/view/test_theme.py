"""Display helpers."""

import unittest
from unittest.mock import patch

from filenamecluster.ui.view import theme

class DisplayTests(unittest.TestCase):
    def test_windows_dpi_helpers_are_best_effort(self):
        with patch.object(theme.sys, "platform", "win32"):
            theme.prepare_process_dpi()
            self.assertGreaterEqual(theme._backing_scale(), 1.0)

