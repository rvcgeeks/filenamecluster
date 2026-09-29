"""FolderRelocation: Apply and Flatten, their confirmations, and the files on disk."""

import tkinter as tk
from unittest.mock import patch

from filenamecluster.core.operations import organize
from filenamecluster.ui.view import Dialogs
from conftest import PHOTOS, WindowCase


class MoveTests(WindowCase):
    def test_apply_moves_while_the_spinner_is_showing(self):
        self.app.controller.load_folder(self.folder)
        seen: dict[str, bool] = {}
        real = organize.move_into_cluster_folders

        def wrapped(directory, clusters):
            seen["busy"] = self.app.model.busy
            return real(directory, clusters)

        with (
            patch.object(organize, "move_into_cluster_folders", wrapped),
            patch.object(Dialogs._messagebox, "askyesno", return_value=True),
            patch.object(Dialogs._messagebox, "showinfo") as info,
        ):
            self.app.controller.apply_clustering()
        self.assertTrue(seen["busy"])
        self.assertFalse(self.app.model.busy)
        self.assertFalse(any(isinstance(child, tk.Toplevel) for child in self.root.winfo_children()))
        info.assert_called_once()
        self.assertIn("disabled", self.app.view.apply_button.state())

    def test_apply_moves_after_confirmation(self):
        self.app.controller.load_folder(self.folder)
        with patch.object(Dialogs._messagebox, "askyesno", return_value=False):
            self.app.controller.apply_clustering()
        self.assertTrue((self.folder / PHOTOS[0]).is_file())

        with (
            patch.object(Dialogs._messagebox, "askyesno", return_value=True),
            patch.object(Dialogs._messagebox, "showinfo") as info,
        ):
            self.app.controller.apply_clustering()
        info.assert_called_once()
        loose = sorted(
            path.name
            for path in self.folder.iterdir()
            if path.is_file() and path.name != "filenamecluster-model.json"
        )
        self.assertEqual(loose, ["notes.txt"])
        self.assertTrue((self.folder / "filenamecluster-model.json").is_file())
        folders = sorted(path.name for path in self.folder.iterdir() if path.is_dir())
        self.assertEqual(len(folders), 3)
        self.assertEqual(len(self.app.model.result.clusters), 2)
        self.assertEqual(len(self.app.view.overview.bars), 2)
        self.assertEqual(len(self.app.view.cluster_tree.get_children()), 2)
        self.assertIn("disabled", self.app.view.apply_button.state())
        self.assertNotIn("disabled", self.app.view.flatten_button.state())
        self.assertIn("preview stays", self.app.view.status_text.get())

    def test_apply_with_no_timestamps_reports_nothing(self):
        plain = self.folder / "plain"
        plain.mkdir()
        (plain / "notes.txt").write_bytes(b"x")
        self.app.controller.load_folder(plain)
        with patch.object(Dialogs._messagebox, "showinfo") as info:
            self.app.controller.apply_clustering()
        self.assertEqual(info.call_args.args[0], "Nothing to move")

    def test_apply_reports_move_errors(self):
        self.app.controller.load_folder(self.folder)
        with (
            patch.object(Dialogs._messagebox, "askyesno", return_value=True),
            patch.object(Dialogs._messagebox, "showerror") as error,
            patch.object(
                organize, "move_into_cluster_folders", side_effect=OSError("disk full")
            ),
        ):
            self.app.controller.apply_clustering()
        error.assert_called_once()
        self.assertTrue((self.folder / PHOTOS[0]).is_file())

    def test_flatten_restores_files_and_keeps_other_folders(self):
        self.app.controller.load_folder(self.folder)
        with (
            patch.object(Dialogs._messagebox, "askyesno", return_value=True),
            patch.object(Dialogs._messagebox, "showinfo"),
        ):
            self.app.controller.apply_clustering()
        with patch.object(Dialogs._messagebox, "askyesno", return_value=False):
            self.app.controller.flatten_clustering()
        self.assertEqual(
            sorted(
                path.name
                for path in self.folder.iterdir()
                if path.is_file() and path.name != "filenamecluster-model.json"
            ),
            ["notes.txt"],
        )
        self.assertEqual(len(self.app.view.overview.bars), 2)

        with (
            patch.object(Dialogs._messagebox, "askyesno", return_value=True),
            patch.object(Dialogs._messagebox, "showinfo") as info,
        ):
            self.app.controller.flatten_clustering()
        info.assert_called_once()
        loose = sorted(
            path.name
            for path in self.folder.iterdir()
            if path.is_file() and path.name != "filenamecluster-model.json"
        )
        self.assertEqual(loose, sorted(PHOTOS))
        self.assertEqual(
            [path.name for path in self.folder.iterdir() if path.is_dir()],
            ["album"],
        )
        self.assertEqual(len(self.app.model.result.clusters), 2)
        self.assertNotIn("disabled", self.app.view.apply_button.state())
        self.assertIn("disabled", self.app.view.flatten_button.state())

    def test_flatten_reports_errors_and_an_empty_folder(self):
        self.app.controller.load_folder(self.folder)
        with patch.object(Dialogs._messagebox, "showinfo") as nothing:
            self.app.controller.flatten_clustering()
        nothing.assert_called_once()
        self.assertEqual(nothing.call_args.args[0], "Nothing to flatten")

        with (
            patch.object(Dialogs._messagebox, "askyesno", return_value=True),
            patch.object(Dialogs._messagebox, "showinfo"),
        ):
            self.app.controller.apply_clustering()
        with (
            patch.object(Dialogs._messagebox, "askyesno", return_value=True),
            patch.object(Dialogs._messagebox, "showerror") as error,
            patch.object(organize, "flatten_cluster_folders", side_effect=OSError("busy")),
        ):
            self.app.controller.flatten_clustering()
        error.assert_called_once()
        self.assertEqual(len(self.app.view.overview.bars), 2)

    def test_flatten_without_folder_does_nothing(self):
        with patch.object(Dialogs._messagebox, "askyesno") as ask:
            self.app.controller.flatten_clustering()
        ask.assert_not_called()

    def test_apply_without_folder_does_nothing(self):
        with patch.object(Dialogs._messagebox, "askyesno") as ask:
            self.app.controller.apply_clustering()
        ask.assert_not_called()
