"""Timeline zoom labels."""

import unittest

from filenamecluster.ui.view.timeline import _describe_zoom


class ZoomLabelTests(unittest.TestCase):
    def test_zoom_labels(self):
        self.assertEqual(_describe_zoom(48), "1 hour = 2 px")
        self.assertEqual(_describe_zoom(5), "1 day = 5 px")
        self.assertEqual(_describe_zoom(0.1), "1 month = 3 px")
