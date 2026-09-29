"""PatternEdits: add, remove, scan, and validate filename patterns."""

import unittest

from filenamecluster.core.parser import TimestampPatterns
from filenamecluster.ui.controller import (
    AppController,
    PatternBlank,
    PatternInvalid,
    PatternValid,
    SystemFiles,
    SystemLogging,
)
from filenamecluster.ui.model import AppModel
from conftest import WindowCase


class PatternEditTests(WindowCase):
    def test_custom_patterns_are_scanned_added_and_removed(self):
        self.app.controller.load_folder(self.folder)
        for iid in self.app.view.pattern_tree.get_children():
            self.app.controller.pattern_committed(iid, "pattern", "")
        self.app.controller.pattern_committed(
            "clock_compact_14",
            "pattern",
            r"shot(?P<y>\d{4})(?P<mo>\d{2})(?P<d>\d{2})(?P<h>\d{2})(?P<mi>\d{2})(?P<s>\d{2})",
        )
        (self.folder / "shot20240301120000.jpg").write_bytes(b"z")
        self.app.controller.refresh()
        names = [item.name for cluster in self.app.model.result.clusters for item in cluster.files]
        self.assertEqual(names, ["shot20240301120000.jpg"])

        before = self.app.view.pattern_tree.get_children()
        self.app.controller.add_pattern_rule()
        added = [iid for iid in self.app.view.pattern_tree.get_children() if iid not in before]
        self.assertEqual(len(added), 1)
        self.assertEqual(self.app.view.pattern_tree.set(added[0], "description"), "Custom pattern")
        self.app.view.pattern_tree.selection_set(added[0])
        self.app.controller.remove_pattern_rule([added[0]])
        self.assertNotIn(added[0], self.app.view.pattern_tree.get_children())


class RecordingUi:
    """Records the dialogs the controller asks the window to show."""

    def __init__(self) -> None:
        self.notices = []

    def tell(self, notice):
        self.notices.append(notice)


class PatternAlertTests(unittest.TestCase):
    def setUp(self):
        self.ui = RecordingUi()
        self.model = AppModel()
        self.controller = AppController(
            self.model, self.ui, files=SystemFiles(), logging=SystemLogging()
        )

    def test_a_compiling_row_is_reported_valid(self):
        self.controller.validate_pattern("Dashed clock", TimestampPatterns().clock_separated)
        self.assertEqual(self.ui.notices[0], PatternValid("Dashed clock"))

    def test_a_blank_row_is_reported_turned_off(self):
        self.controller.validate_pattern("Off", "   ")
        self.assertEqual(self.ui.notices[0], PatternBlank())

    def test_a_broken_row_is_reported_invalid(self):
        self.controller.validate_pattern("Broken", "(")
        notice = self.ui.notices[0]
        self.assertIsInstance(notice, PatternInvalid)
        self.assertIn("invalid regular expression", notice.detail)

    def test_an_unnamed_row_uses_the_custom_label(self):
        self.controller.validate_pattern("  ", TimestampPatterns().clock_separated)
        self.assertEqual(self.ui.notices[0], PatternValid(""))
