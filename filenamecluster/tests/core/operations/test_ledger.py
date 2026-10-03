"""RuleLedger: invalid pattern rows are left out of a scan and saved marked."""

import json

from filenamecluster.core import TimestampPatterns
from conftest import WindowCase


class LedgerTests(WindowCase):
    def test_invalid_rows_are_marked_skipped_and_saved(self):
        self.app.controller.load_folder(self.folder)
        self.assertIn("(?P<y>", self.app.view.pattern_tree.set("clock_compact_sep", "pattern"))
        self.assertEqual(self.app.view.pattern_tree.set("clock_separated", "description"), "Dashed clock")
        self.app.controller.pattern_committed("clock_separated", "pattern", "(")
        self.app.controller.refresh()
        self.assertTrue(self.app.view.pattern_marked("clock_separated"))
        self.assertFalse(self.app.view.pattern_marked("clock_compact_sep"))
        self.assertIn("left out: 1", self.app.view.status_text.get())
        self.assertEqual(len(self.app.model.result.clusters), 2)
        saved = json.loads((self.folder / "filenamecluster-model.json").read_text(encoding="utf-8"))
        marked = {rule["key"]: rule for rule in saved["options"]["rules"]}
        self.assertTrue(marked["clock_separated"]["invalid"])
        self.assertEqual(marked["clock_separated"]["pattern"], "(")
        self.assertNotIn("invalid", marked["clock_compact_sep"])

        self.app.controller.load_folder(self.folder)
        self.assertEqual(self.app.view.pattern_tree.set("clock_separated", "pattern"), "(")
        self.assertTrue(self.app.view.pattern_marked("clock_separated"))

        self.app.controller.pattern_committed(
            "clock_separated", "pattern", TimestampPatterns().clock_separated
        )
        self.app.controller.refresh()
        self.assertFalse(self.app.view.pattern_marked("clock_separated"))
        self.assertNotIn("left out", self.app.view.status_text.get())
