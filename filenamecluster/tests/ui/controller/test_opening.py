"""OpenActions: open an event folder or a Day detail file from the window."""

from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from filenamecluster.ui.controller import SystemFiles
from filenamecluster.ui.view import Dialogs
from conftest import WindowCase


class FolderOpenTests(WindowCase):
    ALBUM = False
    LOAD = True

    def test_double_click_reports_a_missing_event_folder(self):
        self.app.controller.select_cluster(0)
        with patch.object(Dialogs._messagebox, "showwarning") as warn:
            self.app.controller.open_cluster_folder(0)
        warn.assert_called_once()
        title, body = warn.call_args[0][:2]
        self.assertEqual(title, "Cannot open this event")
        self.assertIn("does not exist yet", body)
        self.assertIn(self.app.model.result.clusters[0].name, body)

        with (
            patch.object(self.app.view.overview.canvas, "gettags", return_value=("bar", "c0")),
            patch.object(SystemFiles, "open_folder_window") as opener,
            patch.object(Dialogs._messagebox, "showwarning") as warn,
        ):
            self.app.view.overview._double(SimpleNamespace(x=1, y=1))
        opener.assert_not_called()
        warn.assert_called_once()

        day = self.app.model.result.clusters[0].start.date()
        x0, y0, x1, y1 = self.app.view.calendar._cells[day]
        with patch.object(Dialogs._messagebox, "showwarning") as warn:
            self.app.view.calendar._double(SimpleNamespace(x=(x0 + x1) / 2, y=(y0 + y1) / 2))
        warn.assert_called_once()

        with (
            patch.object(self.app.view.cluster_tree, "identify_row", return_value="0"),
            patch.object(Dialogs._messagebox, "showwarning") as warn,
        ):
            self.app.view._on_cluster_opened(SimpleNamespace(y=10))
        warn.assert_called_once()

    def test_double_click_opens_an_existing_event_folder(self):
        with (
            patch.object(Dialogs._messagebox, "askyesno", return_value=True),
            patch.object(Dialogs._messagebox, "showinfo"),
        ):
            self.app.controller.apply_clustering()
        folder = self.folder / self.app.model.result.clusters[0].name
        self.assertTrue(folder.is_dir())
        self.app.controller.select_cluster(0)
        with patch.object(SystemFiles, "open_folder_window") as opener:
            self.app.controller.open_cluster_folder(0)
            with patch.object(self.app.view.overview.canvas, "gettags", return_value=("bar", "c0")):
                self.app.view.overview._double(SimpleNamespace(x=1, y=1))
            with patch.object(self.app.view.overview.canvas, "gettags", return_value=("bar", "c1")):
                self.app.view.overview._double(SimpleNamespace(x=1, y=1))
        self.assertEqual(opener.call_count, 2)
        self.assertEqual(opener.call_args_list[0].args[0], folder)

    def test_double_click_opens_an_event_folder_with_extra_words(self):
        with (
            patch.object(Dialogs._messagebox, "askyesno", return_value=True),
            patch.object(Dialogs._messagebox, "showinfo"),
        ):
            self.app.controller.apply_clustering()
        cluster = self.app.model.result.clusters[0]
        noted = self.folder / f"Hyderabad trip {cluster.name}"
        (self.folder / cluster.name).rename(noted)
        self.app.controller.select_cluster(0)
        with patch.object(SystemFiles, "open_folder_window") as opener:
            self.app.controller.open_cluster_folder(0)
        opener.assert_called_once_with(noted)

    def test_double_click_in_day_detail_opens_the_file(self):
        name = "IMG_20240101_100000.jpg"
        self.app.controller.show_day(date(2024, 1, 1))
        with (
            patch.object(self.app.view.day_tree, "identify_row", return_value="0"),
            patch.object(SystemFiles, "open_file") as opener,
        ):
            self.app.view._on_day_file(SimpleNamespace(y=10))
        opener.assert_called_once_with(self.folder / name)

        with (
            patch.object(Dialogs._messagebox, "askyesno", return_value=True),
            patch.object(Dialogs._messagebox, "showinfo"),
        ):
            self.app.controller.apply_clustering()
        placed = self.folder / self.app.model.result.clusters[0].name / name
        self.assertTrue(placed.is_file())
        with (
            patch.object(self.app.view.day_tree, "identify_row", return_value="0"),
            patch.object(SystemFiles, "open_file") as opener,
        ):
            self.app.view._on_day_file(SimpleNamespace(y=10))
        opener.assert_called_once_with(placed)

        placed.unlink()
        with (
            patch.object(self.app.view.day_tree, "identify_row", return_value="0"),
            patch.object(SystemFiles, "open_file") as opener,
            patch.object(Dialogs._messagebox, "showwarning") as warn,
        ):
            self.app.view._on_day_file(SimpleNamespace(y=10))
            self.app.view._on_day_file(SimpleNamespace(y=10))
        opener.assert_not_called()
        self.assertEqual(warn.call_args[0][0], "Cannot open this file")

        with (
            patch.object(self.app.view.day_tree, "identify_row", return_value=""),
            patch.object(SystemFiles, "open_file") as opener,
        ):
            self.app.view._on_day_file(SimpleNamespace(y=10))
        opener.assert_not_called()
