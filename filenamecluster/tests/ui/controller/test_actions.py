"""Opening an event folder or a day-detail file from the window."""

import tkinter as tk
import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from filenamecluster.ui.app import FileNameClusterApp
from filenamecluster.ui.controller import actions as action_module
from filenamecluster.ui.controller import files as file_ops
from filenamecluster.ui.model.i18n import set_language

PHOTOS = (
    "IMG_20240101_100000.jpg",
    "IMG_20240101_110000.jpg",
    "IMG_20240102_090000.jpg",
    "IMG_20240120_080000.jpg",
    "notes.txt",
)


def make_root() -> tk.Tk:
    """A Tk interpreter whose window stays withdrawn for the whole test.

    Creating ``Tk`` can map a window before Python runs the next line, so this
    withdraws it immediately and ignores later requests to show, zoom, or fill
    the screen. Tests still build the real widgets. They do not present them.
    """

    try:
        root = tk.Tk()
    except tk.TclError as exc:
        raise unittest.SkipTest(f"no display for Tk: {exc}")
    root.withdraw()
    real_attributes = root.attributes
    real_state = root.state

    def attributes(*args):
        if len(args) >= 2 and args[0] == "-fullscreen" and args[1]:
            return ""
        return real_attributes(*args)

    def state(value=None):
        if value is None:
            return real_state()
        if value != "withdrawn":
            return real_state()
        return real_state(value)

    root.attributes = attributes
    root.state = state
    root.deiconify = lambda: None
    root.withdraw()
    return root

class FolderOpenTests(unittest.TestCase):
    def setUp(self):
        set_language("en")
        self.root = make_root()
        self.app = FileNameClusterApp(self.root)
        self.tmp = TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        for name in PHOTOS:
            (self.folder / name).write_bytes(b"x")
        self.app.load_folder(self.folder)

    def tearDown(self):
        set_language("en")
        self.assertEqual(self.root.state(), "withdrawn")
        self.root.destroy()
        self.tmp.cleanup()

    def test_double_click_reports_a_missing_event_folder(self):
        self.app.select_cluster(0)
        with patch.object(action_module.messagebox, "showwarning") as warn:
            self.app.open_cluster_folder(0)
        warn.assert_called_once()
        title, body = warn.call_args[0][:2]
        self.assertEqual(title, "Cannot open this event")
        self.assertIn("does not exist yet", body)
        self.assertIn(self.app.result.clusters[0].name, body)

        with (
            patch.object(self.app.overview.canvas, "gettags", return_value=("bar", "c0")),
            patch.object(file_ops, "open_folder_window") as opener,
            patch.object(action_module.messagebox, "showwarning") as warn,
        ):
            self.app.overview._double(SimpleNamespace(x=1, y=1))
        opener.assert_not_called()
        warn.assert_called_once()

        day = self.app.result.clusters[0].start.date()
        x0, y0, x1, y1 = self.app.calendar._cells[day]
        with patch.object(action_module.messagebox, "showwarning") as warn:
            self.app.calendar._double(SimpleNamespace(x=(x0 + x1) / 2, y=(y0 + y1) / 2))
        warn.assert_called_once()

        with (
            patch.object(self.app.cluster_tree, "identify_row", return_value="0"),
            patch.object(action_module.messagebox, "showwarning") as warn,
        ):
            self.app._tree_double(SimpleNamespace(y=10))
        warn.assert_called_once()

    def test_double_click_opens_an_existing_event_folder(self):
        with (
            patch.object(action_module.messagebox, "askyesno", return_value=True),
            patch.object(action_module.messagebox, "showinfo"),
        ):
            self.app.apply_clustering()
        folder = self.folder / self.app.result.clusters[0].name
        self.assertTrue(folder.is_dir())
        self.app.select_cluster(0)
        with patch.object(file_ops, "open_folder_window") as opener:
            self.app.open_cluster_folder(0)
            with patch.object(self.app.overview.canvas, "gettags", return_value=("bar", "c0")):
                self.app.overview._double(SimpleNamespace(x=1, y=1))
            with patch.object(self.app.overview.canvas, "gettags", return_value=("bar", "c1")):
                self.app.overview._double(SimpleNamespace(x=1, y=1))
        self.assertEqual(opener.call_count, 2)
        self.assertEqual(opener.call_args_list[0].args[0], folder)

    def test_double_click_in_day_detail_opens_the_file(self):
        name = "IMG_20240101_100000.jpg"
        self.app.show_day(date(2024, 1, 1))
        with (
            patch.object(self.app.day_tree, "identify_row", return_value="0"),
            patch.object(file_ops, "open_file") as opener,
        ):
            self.app._day_file_double(SimpleNamespace(y=10))
        opener.assert_called_once_with(self.folder / name)

        with (
            patch.object(action_module.messagebox, "askyesno", return_value=True),
            patch.object(action_module.messagebox, "showinfo"),
        ):
            self.app.apply_clustering()
        placed = self.folder / self.app.result.clusters[0].name / name
        self.assertTrue(placed.is_file())
        with (
            patch.object(self.app.day_tree, "identify_row", return_value="0"),
            patch.object(file_ops, "open_file") as opener,
        ):
            self.app._day_file_double(SimpleNamespace(y=10))
        opener.assert_called_once_with(placed)

        placed.unlink()
        with (
            patch.object(self.app.day_tree, "identify_row", return_value="0"),
            patch.object(file_ops, "open_file") as opener,
            patch.object(action_module.messagebox, "showwarning") as warn,
        ):
            self.app._day_file_double(SimpleNamespace(y=10))
            self.app._day_file_double(SimpleNamespace(y=10))
        opener.assert_not_called()
        self.assertEqual(warn.call_args[0][0], "Cannot open this file")

        with (
            patch.object(self.app.day_tree, "identify_row", return_value=""),
            patch.object(file_ops, "open_file") as opener,
        ):
            self.app._day_file_double(SimpleNamespace(y=10))
        opener.assert_not_called()

