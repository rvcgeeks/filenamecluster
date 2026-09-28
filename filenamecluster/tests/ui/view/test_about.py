"""About sections, including the pattern guide and this computer's log path."""

import unittest

from filenamecluster.log import log_path
from filenamecluster.ui.view.about import sections
from filenamecluster.ui.model.i18n import set_language


class AboutTests(unittest.TestCase):
    def tearDown(self):
        set_language("en")

    def test_regex_guide_and_log_path_are_separate_sections(self):
        set_language("en")
        rendered = sections()
        titles = [title for title, _body in rendered]
        bodies = [body for _title, body in rendered]
        self.assertEqual(len(titles), len(set(titles)))
        self.assertIn("The little marks", titles)
        self.assertIn("Example: a camera photo", titles)
        self.assertIn("Example: a scanned page", titles)
        regex_titles = {
            "Filename patterns",
            "The little marks",
            "Four kinds of time",
            "Example: a camera photo",
            "Example: a scanned page",
            "The pattern table",
        }
        regex_bodies = [body for title, body in rendered if title in regex_titles]
        guide = "\n".join(regex_bodies)
        logged = next(body for body in bodies if str(log_path()) in body)
        self.assertIn("finditer", guide)
        self.assertIn("(?P<y>", guide)
        self.assertIn("IMG_20240101_101500.jpg", guide)
        self.assertIn("CamScanner 11-21-2024 12.22.jpg", guide)
        self.assertNotIn(str(log_path()), guide)
        self.assertIn("pid=", logged)
        self.assertLess(bodies.index(regex_bodies[0]), bodies.index(logged))
        self.assertLess(bodies.index(regex_bodies[-1]), bodies.index(logged))
