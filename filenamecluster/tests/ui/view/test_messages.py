"""Messages: the status line and dialogs speak the current language."""

from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from filenamecluster.core.operations import OptionFault, OptionField
from filenamecluster.ui.controller import ApplyCreate, PatternValid
from filenamecluster.ui.model import ChooseStatus, OptionProblemStatus, ValueProblemStatus
from filenamecluster.ui.view import Dialogs, t
from conftest import WindowCase


class MessageTests(WindowCase):
    def test_status_keys_redraw_in_the_new_language(self):
        view = self.app.view
        self.app.model.show_choose()
        self.assertIsInstance(self.app.model.status, ChooseStatus)
        english = view.status_text.get()
        self.assertEqual(english, t("choose_status"))
        self.assertEqual(str(view.status.cget("style")), "Status.TLabel")
        self.app.controller.language_chosen("de")
        self.assertNotEqual(view.status_text.get(), english)
        self.app.controller.language_chosen("en")
        self.assertEqual(view.status_text.get(), english)

    def test_option_problems_are_errors_with_a_translated_label(self):
        view = self.app.view
        view.paint_status(OptionProblemStatus(OptionFault.NOT_A_NUMBER, OptionField.FLOOR))
        self.assertIn(t("floor_label"), view.status_text.get())
        self.assertEqual(str(view.status.cget("style")), "Error.TLabel")
        view.paint_status(ValueProblemStatus("plain words"))
        self.assertIn("plain words", view.status_text.get())

    def test_scan_status_counts_left_out_rows(self):
        self.app.controller.load_folder(self.folder)
        self.assertNotIn("left out", self.app.view.status_text.get())
        self.app.view.paint_status(replace(self.app.model.status, left_out=2))
        self.assertIn(t("patterns_left_out", n=2), self.app.view.status_text.get())

    def test_dialogs_receive_translated_titles(self):
        view = self.app.view
        with patch.object(Dialogs, "_messagebox") as boxes:
            boxes.askyesno.return_value = False
            self.assertFalse(
                view.ask(ApplyCreate(Path("album"), files=1, events=2))
            )
            view.tell(PatternValid(""))
            view.tell_info("pattern_valid_title", "pattern_blank_body")
            view.tell_error("pattern_invalid_title", "raw body")
            view.tell_warning("pattern_valid_title", "pattern_blank_body")
        self.assertEqual(
            boxes.askyesno.call_args.args,
            (t("apply"), t("apply_create", path="album", files=1, events=2)),
        )
        self.assertIn(t("custom_pattern"), boxes.showinfo.call_args_list[0].args[1])
        self.assertEqual(boxes.showerror.call_args.args, (t("pattern_invalid_title"), "raw body"))
        self.assertEqual(boxes.showwarning.call_args.args[0], t("pattern_valid_title"))
