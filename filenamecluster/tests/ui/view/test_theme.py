"""Display helpers."""

import sys
import unittest
from unittest.mock import patch

from filenamecluster.ui.view import backing_scale, prepare_process_dpi


class DisplayTests(unittest.TestCase):
    def test_windows_dpi_helpers_are_best_effort(self):
        with patch.object(sys, "platform", "win32"):
            prepare_process_dpi()
            self.assertGreaterEqual(backing_scale(), 1.0)
