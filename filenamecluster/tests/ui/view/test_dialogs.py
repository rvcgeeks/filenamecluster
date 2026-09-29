"""Dialogs: every question and warning is parented on the window."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from filenamecluster.ui.view import Dialogs, t


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
