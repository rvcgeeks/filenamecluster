"""PatternTable: the Validate column opens the alert for each kind of row."""

from unittest.mock import patch

from filenamecluster.ui.view import Dialogs
from conftest import WindowCase


class PatternTableTests(WindowCase):
    def test_validate_reports_each_kind_of_row(self):
        self.app.controller.load_folder(self.folder)
        self.assertEqual(self.app.view.pattern_tree.set("clock_compact_14", "validate"), "Validate")
        with patch.object(Dialogs._messagebox, "showinfo") as valid:
            self.app.view.validate_pattern("clock_compact_14")
        valid.assert_called_once()
        self.app.view.pattern_tree.set("clock_compact_14", "pattern", "(")
        self.app.controller.pattern_committed("clock_compact_14", "pattern", "(")
        with patch.object(Dialogs._messagebox, "showerror") as invalid:
            self.app.view.validate_pattern("clock_compact_14")
        invalid.assert_called_once()
        self.assertIn("invalid regular expression", invalid.call_args.args[1])
        self.app.view.pattern_tree.set("clock_compact_14", "pattern", "")
        self.app.controller.pattern_committed("clock_compact_14", "pattern", "")
        with patch.object(Dialogs._messagebox, "showinfo") as blank:
            self.app.view.validate_pattern("clock_compact_14")
        self.assertIn("blank", blank.call_args.args[1])
