"""The replace-or-skip dialog writes the click onto the clash."""

import unittest

from conftest import make_root
from filenamecluster.ui.model import ClashChoice, NameClash
from filenamecluster.ui.view.name_clash import NameClashDialog


def dialog(root, clash: NameClash, everyone: str | None = None) -> NameClashDialog:
    return NameClashDialog(
        root,
        clash,
        title="Replace or Skip Files",
        body=f'The destination already has a file named "{clash.name}"',
        replace="Replace the file in the destination",
        skip="Skip this file",
        everyone=everyone,
    )


class NameClashDialogTests(unittest.TestCase):
    def setUp(self):
        self.root = make_root()

    def tearDown(self):
        self.root.destroy()

    def test_replace_and_skip_write_the_choice(self):
        clash = NameClash("photo.jpg", 1)
        shown = dialog(self.root, clash)
        self.assertFalse(shown.shows_all)
        self.assertIn('named "photo.jpg"', _texts(shown.window))
        shown.choose_replace()
        self.assertIs(clash.choice, ClashChoice.REPLACE)
        self.assertFalse(clash.for_all)
        self.assertFalse(clash.cancelled)

        again = NameClash("photo.jpg", 4)
        shown = dialog(self.root, again, "Do this for all (4) conflicts")
        self.assertTrue(shown.shows_all)
        self.assertIn("Do this for all (4) conflicts", _texts(shown.window))
        shown.for_all.set(True)
        shown.choose_skip()
        self.assertIs(again.choice, ClashChoice.SKIP)
        self.assertTrue(again.for_all)

    def test_closing_the_dialog_cancels(self):
        clash = NameClash("photo.jpg", 2)
        shown = dialog(self.root, clash, "Do this for all (2) conflicts")
        shown.cancel()
        self.assertTrue(clash.cancelled)
        self.assertIsNone(clash.choice)


def _texts(widget) -> str:
    parts = []
    for child in widget.winfo_children():
        if "text" in child.keys():
            parts.append(str(child.cget("text")))
        parts.append(_texts(child))
    return "\n".join(parts)
