"""Dialogs: every question and warning is parented on the window."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from filenamecluster.ui.view import Dialogs, t
from filenamecluster.ui.view import prompt as prompt_module


class DialogTests(unittest.TestCase):
    def setUp(self):
        self.parent = object()
        self.dialogs = Dialogs(self.parent, t)

    def test_choosing_a_folder_returns_the_path_or_blank(self):
        picker = MagicMock()
        with TemporaryDirectory() as folder, patch.object(Dialogs, "_filedialog", picker):
            picker.askdirectory.return_value = folder
            self.assertEqual(self.dialogs.choose_directory(Path(folder)), folder)
            kwargs = picker.askdirectory.call_args.kwargs
            self.assertEqual(kwargs["initialdir"], Path(folder))
            self.assertIs(kwargs["parent"], self.parent)
            self.assertEqual(kwargs["title"], t("choose_title"))
            picker.askdirectory.return_value = ""
            self.assertEqual(self.dialogs.choose_directory(Path(folder) / "missing"), "")
            self.assertEqual(picker.askdirectory.call_args.kwargs["initialdir"], Path.cwd())

    def test_message_boxes_pass_title_body_and_parent(self):
        boxes = MagicMock()
        boxes.askyesno.return_value = 1
        with patch.object(Dialogs, "_messagebox", boxes):
            self.assertIs(self.dialogs.ask_yes_no("Title", "Body"), True)
            self.dialogs.info("i", "info body")
            self.dialogs.error("e", "error body")
            self.dialogs.warning("w", "warning body")
        boxes.askyesno.assert_called_once_with("Title", "Body", parent=self.parent)
        boxes.showinfo.assert_called_once_with("i", "info body", parent=self.parent)
        boxes.showerror.assert_called_once_with("e", "error body", parent=self.parent)
        boxes.showwarning.assert_called_once_with("w", "warning body", parent=self.parent)

    def test_apply_questions_use_the_timeout_without_opening_a_window(self):
        with patch.object(prompt_module, "yes_no", return_value=True) as ask:
            self.assertTrue(self.dialogs.ask_yes_no("Apply clustering", "Move the files"))
            self.dialogs.info("Clustering applied", "Moved 1 file.", timed=True)
        question, done = ask.call_args_list
        self.assertEqual(question.args, (self.parent, "Apply clustering", "Move the files"))
        self.assertEqual(question.kwargs["timeout"], prompt_module.PROMPT_TIMEOUT_SECONDS)
        self.assertEqual(question.kwargs["ok"], t("prompt_ok"))
        self.assertEqual(question.kwargs["cancel"], t("prompt_cancel"))
        self.assertEqual(
            question.kwargs["countdown"],
            t("prompt_countdown", seconds="{seconds}"),
        )
        self.assertIsNone(done.kwargs["cancel"])
        self.assertEqual(done.kwargs["timeout"], prompt_module.PROMPT_TIMEOUT_SECONDS)

    def test_cancel_is_not_ok_and_the_timer_running_out_is(self):
        self.assertFalse(prompt_module.closed_answer(t("prompt_cancel")))
        self.assertTrue(prompt_module.closed_answer(None))
        self.assertEqual(prompt_module.countdown_step(prompt_module.PROMPT_TIMEOUT_SECONDS), (29, False))
        shown, expired = prompt_module.countdown_step(1)
        self.assertEqual(shown, 0)
        self.assertTrue(expired)
        self.assertEqual(
            t("prompt_countdown", seconds="{seconds}").format(seconds=prompt_module.PROMPT_TIMEOUT_SECONDS),
            "OK in 30s",
        )

    def test_a_separate_input_asks_move_or_copy_without_opening_a_window(self):
        with patch.object(prompt_module, "choose", return_value="copy") as choose:
            self.assertEqual(self.dialogs.ask_transfer("Title", "Body"), "copy")
        self.assertEqual(choose.call_args.args[:3], (self.parent, "Title", "Body"))
        self.assertEqual(choose.call_args.kwargs["default"], "move")
        self.assertEqual(choose.call_args.kwargs["timeout"], prompt_module.PROMPT_TIMEOUT_SECONDS)
        self.assertEqual(
            [key for key, _label in choose.call_args.kwargs["options"]],
            ["move", "copy"],
        )
        self.assertEqual(prompt_module.timeout_pick("move"), "move")
