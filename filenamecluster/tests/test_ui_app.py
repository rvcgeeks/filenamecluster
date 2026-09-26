"""Drive the real window with a hidden Tk root."""

import tkinter as tk
import unittest
from datetime import date, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from filenamecluster.core.parse import TimestampPatterns
from filenamecluster.ui import app as app_module
from filenamecluster.ui import theme
from filenamecluster.ui.app import ClusterApp
from filenamecluster.ui.i18n import set_language, t

PHOTOS = (
    "IMG_20240101_100000.jpg",
    "IMG_20240101_110000.jpg",
    "IMG_20240102_090000.jpg",
    "IMG_20240120_080000.jpg",
    "notes.txt",
)


def make_root() -> tk.Tk:
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        raise unittest.SkipTest(f"no display for Tk: {exc}")
    root.withdraw()
    return root


class AppTests(unittest.TestCase):
    def setUp(self):
        set_language("en")
        self.tmp = TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        for name in PHOTOS:
            (self.folder / name).write_bytes(b"x")
        (self.folder / "album").mkdir()
        self.root = make_root()
        self.app = ClusterApp(self.root)
        self.root.update_idletasks()

    def tearDown(self):
        set_language("en")
        theme.use_script(self.root, self.app.fonts, "en")
        self.root.destroy()
        self.tmp.cleanup()

    def test_starts_empty_with_apply_disabled(self):
        self.assertFalse(self.app.refresh())
        self.assertIn("disabled", self.app.apply_button.state())
        self.assertIn("disabled", self.app.flatten_button.state())
        self.assertIsNone(self.app.overview.scale)
        about = self.app.about_text.get("1.0", "end")
        self.assertIn("Apply clustering", about)
        self.assertIn("Flatten clustering", about)
        self.assertIn("filenamecluster-model.json", about)
        self.assertIn("timestamps only", about)
        self.assertIn("1990 and 2100", about)
        self.assertIn("Filename patterns", about)

    def test_choosing_a_folder_previews_without_moving(self):
        with patch.object(app_module.filedialog, "askdirectory", return_value=str(self.folder)):
            self.app.choose_folder()
        result = self.app.result
        self.assertEqual(len(result.clusters), 2)
        self.assertEqual(result.file_count, 4)
        self.assertEqual(len(self.app.cluster_tree.get_children()), 2)
        self.assertEqual(len(self.app.skipped_tree.get_children()), 2)
        self.assertEqual(len(self.app.overview.bars), 2)
        self.assertEqual(self.app.selected_day, date(2024, 1, 1))
        self.assertEqual(len(self.app.day_tree.get_children()), 2)
        self.assertIn("2 events", self.app.status_text.get())
        self.assertNotIn("disabled", self.app.apply_button.state())
        self.assertIn("disabled", self.app.flatten_button.state())
        self.assertTrue((self.folder / PHOTOS[0]).is_file())

        with patch.object(app_module.filedialog, "askdirectory", return_value=""):
            self.app.choose_folder()
        self.assertEqual(self.app.directory, self.folder)

    def test_selecting_clusters_and_days_syncs_every_view(self):
        self.app.load_folder(self.folder)
        self.app.select_cluster(1)
        self.assertEqual(self.app.selected_cluster, 1)
        self.assertEqual(self.app.overview.selected, 1)
        self.assertEqual(self.app.calendar.selected_cluster, 1)
        self.assertEqual(self.app.cluster_tree.selection(), ("1",))
        self.assertEqual(self.app.selected_day, date(2024, 1, 20))
        self.app.select_cluster(99)
        self.assertEqual(self.app.selected_cluster, 1)

        self.app.cluster_tree.selection_set("0")
        self.app._tree_selected()
        self.assertEqual(self.app.selected_cluster, 0)

        self.app._day_clicked(date(2024, 1, 2))
        self.assertEqual(self.app.selected_day, date(2024, 1, 2))
        self.assertEqual(len(self.app.day_tree.get_children()), 1)
        self.app._day_clicked(date(2024, 1, 10))
        self.assertEqual(len(self.app.day_tree.get_children()), 0)
        self.assertEqual(self.app.selected_cluster, 0)

        self.app._timeline_clicked(datetime(2024, 1, 20, 9))
        self.assertEqual(self.app.selected_cluster, 1)

    def test_bad_options_are_reported(self):
        self.app.load_folder(self.folder)
        self.app.option_vars["floor"].set(800)
        self.assertFalse(self.app.refresh())
        self.assertIn("ceiling", self.app.status_text.get())
        self.assertEqual(str(self.app.status.cget("style")), "Error.TLabel")
        self.app.option_inputs["floor"].delete(0, "end")
        self.app.option_inputs["floor"].insert(0, "abc")
        self.assertFalse(self.app.refresh())
        self.assertIn("Never split", self.app.status_text.get())
        self.app.restore_defaults()
        self.assertEqual(len(self.app.result.clusters), 2)

    def test_pattern_options_are_editable(self):
        self.app.load_folder(self.folder)
        self.assertIn("(?P<y>", self.app.pattern_vars["clock_compact_sep"].get())
        self.assertEqual(self.app.limit_vars["min_year"].get(), 1990)
        self.assertEqual(self.app.limit_vars["prec_clock"].get(), 30)

        self.app.pattern_vars["clock_separated"].set("(")
        self.assertFalse(self.app.refresh())
        self.assertIn("Dashed clock", self.app.status_text.get())

        self.app.pattern_vars["clock_separated"].set(TimestampPatterns().clock_separated)
        self.app.limit_vars["min_year"].set(2100)
        self.app.limit_vars["max_year"].set(1990)
        self.assertFalse(self.app.refresh())
        self.assertIn("minimum year", self.app.status_text.get())

        self.app.limit_vars["min_year"].set(0)
        self.assertFalse(self.app.refresh())
        self.assertIn("between", self.app.status_text.get())

        self.app.limit_inputs["min_year"].delete(0, "end")
        self.app.limit_inputs["min_year"].insert(0, "nope")
        self.app.limit_vars["max_year"].set(2100)
        self.assertFalse(self.app.refresh())
        self.assertIn("Minimum year", self.app.status_text.get())

        self.app.restore_defaults()
        self.assertEqual(len(self.app.result.clusters), 2)
        self.assertEqual(self.app.limit_vars["min_year"].get(), 1990)

        for key in self.app.pattern_vars:
            self.app.pattern_vars[key].set("")
        self.app.pattern_vars["clock_compact_14"].set(
            r"shot(?P<y>\d{4})(?P<mo>\d{2})(?P<d>\d{2})(?P<h>\d{2})(?P<mi>\d{2})(?P<s>\d{2})"
        )
        (self.folder / "shot20240301120000.jpg").write_bytes(b"z")
        self.assertTrue(self.app.refresh())
        names = [item.name for cluster in self.app.result.clusters for item in cluster.files]
        self.assertEqual(names, ["shot20240301120000.jpg"])

        self.assertEqual(self.app._scroll_options(SimpleNamespace(delta=120)), "break")
        self.assertEqual(self.app._scroll_options(SimpleNamespace(delta=-120)), "break")

    def test_tighter_options_split_more(self):
        self.app.load_folder(self.folder)
        self.app.option_vars["floor"].set(2)
        self.app.option_vars["ceiling"].set(3)
        self.assertTrue(self.app.refresh())
        self.assertEqual(len(self.app.result.clusters), 3)

    def test_model_file_is_visible_and_holds_only_the_learned_boundary(self):
        self.app.load_folder(self.folder)
        model_file = self.folder / "filenamecluster-model.json"
        self.assertTrue(model_file.is_file())
        self.assertFalse(model_file.name.startswith("."))
        self.assertFalse(hasattr(self.app, "split_button"))
        text = model_file.read_text(encoding="utf-8")
        self.assertIn("learned", text)
        self.assertNotIn("splits", text)
        self.assertNotIn("merges", text)
        self.assertNotIn("note", text)

    def test_unreadable_folder_is_reported(self):
        self.assertFalse(self.app.load_folder(self.folder / "missing"))
        self.assertIn("Could not read", self.app.status_text.get())

    def test_apply_moves_after_confirmation(self):
        self.app.load_folder(self.folder)
        with patch.object(app_module.messagebox, "askyesno", return_value=False):
            self.app.apply_clustering()
        self.assertTrue((self.folder / PHOTOS[0]).is_file())

        with (
            patch.object(app_module.messagebox, "askyesno", return_value=True),
            patch.object(app_module.messagebox, "showinfo") as info,
        ):
            self.app.apply_clustering()
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
        self.assertEqual(len(self.app.result.clusters), 2)
        self.assertEqual(len(self.app.overview.bars), 2)
        self.assertEqual(len(self.app.cluster_tree.get_children()), 2)
        self.assertIn("disabled", self.app.apply_button.state())
        self.assertNotIn("disabled", self.app.flatten_button.state())
        self.assertIn("preview stays", self.app.status_text.get())

    def test_apply_with_no_timestamps_reports_nothing(self):
        plain = self.folder / "plain"
        plain.mkdir()
        (plain / "notes.txt").write_bytes(b"x")
        self.app.load_folder(plain)
        with patch.object(app_module.messagebox, "showinfo") as info:
            self.app.apply_clustering()
        self.assertEqual(info.call_args.args[0], "Nothing to move")

    def test_apply_reports_move_errors(self):
        self.app.load_folder(self.folder)
        with (
            patch.object(app_module.messagebox, "askyesno", return_value=True),
            patch.object(app_module.messagebox, "showerror") as error,
            patch.object(
                app_module, "move_into_cluster_folders", side_effect=OSError("disk full")
            ),
        ):
            self.app.apply_clustering()
        error.assert_called_once()
        self.assertTrue((self.folder / PHOTOS[0]).is_file())

    def test_flatten_restores_files_and_keeps_other_folders(self):
        self.app.load_folder(self.folder)
        with (
            patch.object(app_module.messagebox, "askyesno", return_value=True),
            patch.object(app_module.messagebox, "showinfo"),
        ):
            self.app.apply_clustering()
        with patch.object(app_module.messagebox, "askyesno", return_value=False):
            self.app.flatten_clustering()
        self.assertEqual(
            sorted(
                path.name
                for path in self.folder.iterdir()
                if path.is_file() and path.name != "filenamecluster-model.json"
            ),
            ["notes.txt"],
        )
        self.assertEqual(len(self.app.overview.bars), 2)

        with (
            patch.object(app_module.messagebox, "askyesno", return_value=True),
            patch.object(app_module.messagebox, "showinfo") as info,
        ):
            self.app.flatten_clustering()
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
        self.assertEqual(len(self.app.result.clusters), 2)
        self.assertNotIn("disabled", self.app.apply_button.state())
        self.assertIn("disabled", self.app.flatten_button.state())

    def test_flatten_reports_errors_and_an_empty_folder(self):
        self.app.load_folder(self.folder)
        with patch.object(app_module.messagebox, "showinfo") as nothing:
            self.app.flatten_clustering()
        nothing.assert_called_once()
        self.assertEqual(nothing.call_args.args[0], "Nothing to flatten")

        with (
            patch.object(app_module.messagebox, "askyesno", return_value=True),
            patch.object(app_module.messagebox, "showinfo"),
        ):
            self.app.apply_clustering()
        with (
            patch.object(app_module.messagebox, "askyesno", return_value=True),
            patch.object(app_module.messagebox, "showerror") as error,
            patch.object(app_module, "flatten_cluster_folders", side_effect=OSError("busy")),
        ):
            self.app.flatten_clustering()
        error.assert_called_once()
        self.assertEqual(len(self.app.overview.bars), 2)

    def test_choosing_another_folder_replaces_the_preview(self):
        self.app.load_folder(self.folder)
        with (
            patch.object(app_module.messagebox, "askyesno", return_value=True),
            patch.object(app_module.messagebox, "showinfo"),
        ):
            self.app.apply_clustering()
        self.assertEqual(len(self.app.overview.bars), 2)
        other = self.folder / "next"
        other.mkdir()
        (other / "IMG_20240201_100000.jpg").write_bytes(b"z")
        self.app.load_folder(other)
        self.assertEqual(len(self.app.result.clusters), 1)
        self.assertEqual(self.app.result.clusters[0].files[0].name, "IMG_20240201_100000.jpg")

    def test_flatten_without_folder_does_nothing(self):
        with patch.object(app_module.messagebox, "askyesno") as ask:
            self.app.flatten_clustering()
        ask.assert_not_called()

    def test_apply_without_folder_does_nothing(self):
        with patch.object(app_module.messagebox, "askyesno") as ask:
            self.app.apply_clustering()
        ask.assert_not_called()


class WidgetTests(unittest.TestCase):
    def setUp(self):
        set_language("en")
        self.root = make_root()
        self.app = ClusterApp(self.root)
        self.tmp = TemporaryDirectory()
        folder = Path(self.tmp.name)
        for name in PHOTOS:
            (folder / name).write_bytes(b"x")
        self.app.load_folder(folder)
        self.root.update_idletasks()

    def tearDown(self):
        set_language("en")
        theme.use_script(self.root, self.app.fonts, "en")
        self.root.destroy()
        self.tmp.cleanup()

    def test_timeline_zoom_fit_scroll_and_clicks(self):
        view = self.app.overview
        before = view.scale.pixels_per_day
        view.zoom_in()
        self.assertGreater(view.scale.pixels_per_day, before)
        view.zoom_out()
        self.assertAlmostEqual(view.scale.pixels_per_day, before)
        view._zoom_wheel(SimpleNamespace(delta=120, x=10))
        view._zoom_wheel(SimpleNamespace(delta=-120, x=10))
        self.assertEqual(view._wheel(SimpleNamespace(delta=1)), "break")
        self.assertEqual(view._wheel(SimpleNamespace(delta=-1)), "break")
        view.fit()
        self.assertIn("=", view.scale_label.cget("text"))

        bar = view.bars[1]
        with patch.object(view.canvas, "gettags", return_value=("current", "bar", "c1", "rect")):
            view._clicked(SimpleNamespace(x=bar.x0 + 1, y=0))
        self.assertEqual(self.app.selected_cluster, 1)
        view.canvas.xview_moveto(0)
        offset = view.canvas.canvasx(0)
        with patch.object(view.canvas, "gettags", return_value=()):
            view._clicked(SimpleNamespace(x=view.bars[0].x0 + 1 - offset, y=0))
        self.assertEqual(self.app.selected_day, date(2024, 1, 1))

        view.show(())
        view.zoom_in()
        view.fit()
        view._clicked(SimpleNamespace(x=0, y=0))
        self.assertIsNone(view.scale)

    def test_zoom_labels(self):
        from filenamecluster.ui.timeline import _describe_zoom

        self.assertEqual(_describe_zoom(48), "1 hour = 2 px")
        self.assertEqual(_describe_zoom(5), "1 day = 5 px")
        self.assertEqual(_describe_zoom(0.1), "1 month = 3 px")

    def test_language_switches_and_english_returns(self):
        self.assertEqual(self.app.apply_button.cget("text"), "Apply clustering")
        self.app.language_var.set("Deutsch")
        self.app._language_changed()
        self.assertEqual(self.app.apply_button.cget("text"), t("apply"))
        self.assertNotEqual(self.app.apply_button.cget("text"), "Apply clustering")
        self.app.language_var.set("English")
        self.app._language_changed()
        self.assertEqual(self.app.apply_button.cget("text"), "Apply clustering")
        self.assertIn("Flatten clustering", self.app.about_text.get("1.0", "end"))

    def test_calendar_navigation_and_clicks(self):
        calendar = self.app.calendar
        self.assertEqual((calendar.year, calendar.month), (2024, 1))
        calendar.move(1)
        self.assertEqual((calendar.year, calendar.month), (2024, 2))
        calendar.previous_event_month()
        self.assertEqual((calendar.year, calendar.month), (2024, 1))
        calendar.previous_event_month()
        self.assertEqual((calendar.year, calendar.month), (2024, 1))
        calendar.show_month(2023, 5)
        calendar.next_event_month()
        self.assertEqual((calendar.year, calendar.month), (2024, 1))
        calendar.next_event_month()
        self.assertEqual((calendar.year, calendar.month), (2024, 1))

        x0, y0, x1, y1 = calendar._cells[date(2024, 1, 20)]
        calendar._clicked(SimpleNamespace(x=(x0 + x1) / 2, y=(y0 + y1) / 2))
        self.assertEqual(self.app.selected_day, date(2024, 1, 20))
        self.assertEqual(self.app.selected_cluster, 1)
        self.assertIsNone(calendar.day_at(-5, -5))
        calendar._clicked(SimpleNamespace(x=-5, y=-5))

        day_view = self.app.day_view
        with patch.object(day_view.canvas, "gettags", return_value=("bar", "c1")):
            day_view._clicked(SimpleNamespace(x=day_view.bars[0].x0, y=0))
        self.assertEqual(self.app.selected_cluster, 1)
        with patch.object(day_view.canvas, "gettags", return_value=()):
            day_view._clicked(SimpleNamespace(x=0, y=0))


class MainTests(unittest.TestCase):
    def test_main_builds_the_app_and_runs_the_loop(self):
        root = make_root()
        with (
            patch.object(app_module.tk, "Tk", return_value=root),
            patch.object(root, "mainloop") as loop,
        ):
            self.assertEqual(app_module.main(), 0)
        loop.assert_called_once()
        root.destroy()


if __name__ == "__main__":
    unittest.main()
