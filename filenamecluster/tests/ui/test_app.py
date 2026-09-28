"""Drive the widgets with a Tk root that is never mapped onto the screen."""

import json
import tkinter as tk
import unittest
from datetime import date, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from filenamecluster.core.parse import TimestampPatterns
from filenamecluster.log import log_path, logging_enabled, set_logging_enabled
from filenamecluster.ui import app as app_module
from filenamecluster.ui.app import FileNameClusterApp
from filenamecluster.ui.controller import actions as action_module
from filenamecluster.ui.model.i18n import set_language, t
from filenamecluster.ui.view import theme

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

class AppTests(unittest.TestCase):
    def setUp(self):
        set_language("en")
        set_logging_enabled(False)
        self.tmp = TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        for name in PHOTOS:
            (self.folder / name).write_bytes(b"x")
        (self.folder / "album").mkdir()
        self.root = make_root()
        self.app = FileNameClusterApp(self.root)
        self.root.update_idletasks()

    def tearDown(self):
        set_language("en")
        set_logging_enabled(False)
        theme.use_script(self.root, self.app.fonts, "en")
        self.assertEqual(self.root.state(), "withdrawn")
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
        self.assertIn("(?P<y>", about)
        self.assertIn("finditer", about)
        self.assertIn("pid=", about)
        self.assertIn(str(log_path()), about)

    def test_options_logging_switch_starts_off(self):
        self.assertEqual(self.app.logging_switch.cget("text"), "Write application log")
        self.assertFalse(self.app.logging_var.get())
        self.assertFalse(logging_enabled())
        self.app.logging_var.set(True)
        self.app._logging_toggled()
        self.assertTrue(logging_enabled())
        self.app.logging_var.set(False)
        self.app._logging_toggled()
        self.assertFalse(logging_enabled())

    def test_choosing_a_folder_previews_without_moving(self):
        with patch.object(action_module.filedialog, "askdirectory", return_value=str(self.folder)):
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

        with patch.object(action_module.filedialog, "askdirectory", return_value=""):
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

    def test_cluster_list_sorts_by_number_and_file_count(self):
        self.app.load_folder(self.folder)
        tree = self.app.cluster_tree
        counts = [int(tree.set(iid, "files")) for iid in tree.get_children()]
        self.assertGreater(max(counts), min(counts))
        self.assertEqual(tree.heading("number")["text"], "#")
        self.assertEqual(tree.heading("files")["text"], "Files")
        self.assertNotEqual(tree.heading("number")["command"], "")
        self.assertNotEqual(tree.heading("files")["command"], "")
        self.assertEqual(tree.heading("name")["command"], "")
        self.assertIn("major ones", self.app.about_text.get("1.0", "end"))

        self.app.sort_clusters("files")
        self.assertEqual(tree.heading("files")["text"], "Files ↑")
        self.assertEqual(tree.heading("number")["text"], "#")
        ordered = [int(tree.set(iid, "files")) for iid in tree.get_children()]
        self.assertEqual(ordered, sorted(ordered))

        self.app.sort_clusters("files")
        self.assertEqual(tree.heading("files")["text"], "Files ↓")
        ordered = [int(tree.set(iid, "files")) for iid in tree.get_children()]
        self.assertEqual(ordered, sorted(ordered, reverse=True))
        self.assertEqual(tree.get_children()[0], "0")

        self.app.sort_clusters("number")
        self.assertEqual(tree.heading("number")["text"], "# ↑")
        self.assertEqual(tree.heading("files")["text"], "Files")
        numbers = [int(tree.set(iid, "number")) for iid in tree.get_children()]
        self.assertEqual(numbers, sorted(numbers))

        self.app.sort_clusters("number")
        self.assertEqual(tree.heading("number")["text"], "# ↓")
        numbers = [int(tree.set(iid, "number")) for iid in tree.get_children()]
        self.assertEqual(numbers, sorted(numbers, reverse=True))

        tree.selection_set("0")
        self.app._tree_selected()
        self.assertEqual(self.app.selected_cluster, 0)
        self.app._apply_cluster_sort()
        self.assertEqual(tree.selection(), ("0",))

        self.app.refresh()
        numbers = [int(tree.set(iid, "number")) for iid in tree.get_children()]
        self.assertEqual(numbers, sorted(numbers, reverse=True))
        self.assertEqual(tree.heading("number")["text"], "# ↓")

        self.app.language_var.set("Deutsch")
        self.app._language_changed()
        self.assertTrue(tree.heading("number")["text"].endswith("↓"))
        self.assertIn(t("col_number"), tree.heading("number")["text"])

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
        self.assertIn("(?P<y>", self.app.pattern_tree.set("clock_compact_sep", "pattern"))
        self.assertEqual(self.app.pattern_tree.set("clock_separated", "description"), "Dashed clock")
        self.assertEqual(self.app.limit_vars["min_year"].get(), 1990)
        self.assertEqual(self.app.limit_vars["prec_clock"].get(), 30)

        self.app.pattern_tree.set("clock_separated", "pattern", "(")
        self.assertFalse(self.app.refresh())
        self.assertIn("Dashed clock", self.app.status_text.get())

        self.app.pattern_tree.set(
            "clock_separated", "pattern", TimestampPatterns().clock_separated
        )
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

        for iid in self.app.pattern_tree.get_children():
            self.app.pattern_tree.set(iid, "pattern", "")
        self.app.pattern_tree.set(
            "clock_compact_14",
            "pattern",
            r"shot(?P<y>\d{4})(?P<mo>\d{2})(?P<d>\d{2})(?P<h>\d{2})(?P<mi>\d{2})(?P<s>\d{2})",
        )
        (self.folder / "shot20240301120000.jpg").write_bytes(b"z")
        self.assertTrue(self.app.refresh())
        names = [item.name for cluster in self.app.result.clusters for item in cluster.files]
        self.assertEqual(names, ["shot20240301120000.jpg"])

        before = self.app.pattern_tree.get_children()
        self.app.add_pattern_rule()
        added = [iid for iid in self.app.pattern_tree.get_children() if iid not in before]
        self.assertEqual(len(added), 1)
        self.assertEqual(self.app.pattern_tree.set(added[0], "description"), "Custom pattern")
        self.app.pattern_tree.selection_set(added[0])
        self.app.remove_pattern_rule()
        self.assertNotIn(added[0], self.app.pattern_tree.get_children())

        self.assertEqual(str(self.app.options_rows.cget("orient")), "vertical")
        self.assertEqual(str(self.app.options_columns.cget("orient")), "horizontal")
        self.assertEqual(len(self.app.options_rows.panes()), 2)
        self.assertEqual(len(self.app.options_columns.panes()), 3)
        limits = self.app.root.nametowidget(self.app.options_columns.panes()[1])
        limits.event_generate("<Configure>", width=520, height=400)
        hints = [
            child
            for child in limits.winfo_children()
            if str(child.cget("style")) == "Muted.TLabel"
        ]
        self.assertEqual(int(hints[0].cget("wraplength")), 492)
        patterns = self.app.root.nametowidget(self.app.options_rows.panes()[0])
        patterns.event_generate("<Configure>", width=420, height=300)
        self.assertEqual(int(patterns.winfo_children()[0].cget("wraplength")), 400)
        self.app._place_equal_columns(self.app.options_columns.winfo_width() or 900)
        widths = [
            int(self.app.options_columns.paneconfigure(pane_id, "width")[-1])
            for pane_id in self.app.options_columns.panes()
        ]
        self.assertEqual(widths[0], widths[1])
        self.assertEqual(widths[1], widths[2])
        self.assertGreater(widths[0], 0)

    def test_saved_options_override_defaults_and_keep_learned(self):
        self.app.load_folder(self.folder)
        path = self.folder / "filenamecluster-model.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        self.assertIsNone(raw["learned"])
        self.assertEqual(raw["options"]["floor_hours"], 3)
        self.assertIn("rules", raw["options"])
        raw["options"]["floor_hours"] = 2
        raw["options"]["ceiling_hours"] = 3
        path.write_text(json.dumps(raw), encoding="utf-8")
        self.app.option_vars["floor"].set(3)
        self.app.option_vars["ceiling"].set(720)
        self.app.load_folder(self.folder)
        self.assertEqual(self.app.option_vars["floor"].get(), 2)
        self.assertEqual(self.app.option_vars["ceiling"].get(), 3)
        self.assertEqual(len(self.app.result.clusters), 3)
        again = json.loads(path.read_text(encoding="utf-8"))
        self.assertIsNone(again["learned"])
        self.assertEqual(again["options"]["floor_hours"], 2)
        self.assertEqual(again["options"]["ceiling_hours"], 3)

        again["options"] = {"floor_hours": "nope"}
        path.write_text(json.dumps(again), encoding="utf-8")
        self.app.load_folder(self.folder)
        self.assertEqual(self.app.option_vars["floor"].get(), 3)
        self.assertEqual(len(self.app.result.clusters), 2)
        restored = json.loads(path.read_text(encoding="utf-8"))
        self.assertIsNone(restored["learned"])
        self.assertEqual(restored["options"]["floor_hours"], 3)

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
        self.assertIn("options", text)
        self.assertNotIn("splits", text)
        self.assertNotIn("merges", text)
        self.assertNotIn("note", text)

    def test_options_model_view_matches_the_json_and_stays_read_only(self):
        self.assertEqual(
            [self.app.model_tree.set(row, "value") for row in self.app.model_tree.get_children()],
            ["—", "—", "—", "—"],
        )
        self.assertEqual(self.app.model_tree.bind("<Double-1>"), "")
        self.app.load_folder(self.folder)
        raw = json.loads((self.folder / "filenamecluster-model.json").read_text(encoding="utf-8"))
        self.assertIsNone(raw["learned"])
        self.assertEqual(
            [self.app.model_tree.set(row, "value") for row in ("within_hours", "between_hours", "boundary_hours", "separated")],
            ["null", "null", "null", "null"],
        )

        rich = self.folder / "rich"
        rich.mkdir()
        for name in (
            "IMG_20240101_100000.jpg",
            "IMG_20240101_140000.jpg",
            "IMG_20240101_200000.jpg",
            "IMG_20240102_040000.jpg",
            "IMG_20240104_040000.jpg",
            "IMG_20240107_040000.jpg",
            "IMG_20240111_040000.jpg",
        ):
            (rich / name).write_bytes(b"x")
        self.app.load_folder(rich)
        learned = json.loads((rich / "filenamecluster-model.json").read_text(encoding="utf-8"))["learned"]
        self.assertIsNotNone(learned)
        for key in ("within_hours", "between_hours", "boundary_hours"):
            self.assertEqual(self.app.model_tree.set(key, "parameter"), f"learned.{key}")
            self.assertEqual(self.app.model_tree.set(key, "value"), json.dumps(learned[key]))
        self.assertEqual(
            self.app.model_tree.set("separated", "value"),
            "true" if learned["separated"] else "false",
        )
        self.assertIsNone(self.app._pattern_editor)
        raw_options = json.loads((rich / "filenamecluster-model.json").read_text(encoding="utf-8"))
        self.assertIn("options", raw_options)
        self.assertEqual(raw_options["options"]["floor_hours"], self.app.option_vars["floor"].get())

    def test_unreadable_folder_is_reported(self):
        self.assertFalse(self.app.load_folder(self.folder / "missing"))
        self.assertIn("Could not read", self.app.status_text.get())

    def test_lock_inputs_disables_buttons_and_options_only(self):
        self.app.load_folder(self.folder)
        self.assertNotIn("disabled", self.app.apply_button.state())
        self.app.lock_inputs()
        self.assertIn("disabled", self.app.apply_button.state())
        self.assertEqual(str(self.app.option_inputs["floor"].cget("state")), "disabled")
        self.assertEqual(str(self.app.limit_inputs["min_year"].cget("state")), "disabled")
        self.assertEqual(str(self.app.logging_switch.cget("state")), "disabled")
        self.app._begin_pattern_edit(self.app.pattern_tree.get_children()[0], "pattern")
        self.assertIsNone(self.app._pattern_editor)
        self.assertEqual(str(self.app.overview.canvas.cget("state")), "normal")
        self.assertEqual(str(self.app.calendar.canvas.cget("state")), "normal")
        self.assertEqual(str(self.app.cluster_tree.cget("selectmode")), "browse")
        self.app.unlock_inputs()
        self.assertNotIn("disabled", self.app.apply_button.state())
        self.assertIn("disabled", self.app.flatten_button.state())

    def test_every_wait_says_why_before_and_after_confirmation(self):
        keys: list[str] = []
        original = action_module.AppController._run_disk

        def wrapped(controller, message_key, work, on_done):
            keys.append(message_key)
            return original(controller, message_key, work, on_done)

        with patch.object(action_module.AppController, "_run_disk", wrapped):
            self.app.load_folder(self.folder)
            self.app.refresh()
        self.assertEqual(keys, ["busy_open", "busy_preview"])

        keys.clear()
        with (
            patch.object(action_module.AppController, "_run_disk", wrapped),
            patch.object(action_module.messagebox, "askyesno", return_value=True),
            patch.object(action_module.messagebox, "showinfo"),
        ):
            self.app.apply_clustering()
        self.assertEqual(keys, ["busy_apply_check", "busy_apply"])

        keys.clear()
        with (
            patch.object(action_module.AppController, "_run_disk", wrapped),
            patch.object(action_module.messagebox, "askyesno", return_value=True),
            patch.object(action_module.messagebox, "showinfo"),
        ):
            self.app.flatten_clustering()
        self.assertEqual(keys, ["busy_flatten_check", "busy_flatten", "busy_after_flatten"])
        for key in ("busy_open", "busy_preview", "busy_apply_check", "busy_apply",
                    "busy_flatten_check", "busy_flatten", "busy_after_flatten", "busy_after_error"):
            self.assertNotEqual(action_module.t(key), key)
        self.assertIn("No clusters", action_module.t("busy_flatten_check"))

    def test_apply_moves_while_the_spinner_is_showing(self):
        self.app.load_folder(self.folder)
        seen: dict[str, bool] = {}
        real = action_module.move_into_cluster_folders

        def wrapped(directory, clusters):
            seen["busy"] = self.app._busy
            return real(directory, clusters)

        with (
            patch.object(action_module, "move_into_cluster_folders", wrapped),
            patch.object(action_module.messagebox, "askyesno", return_value=True),
            patch.object(action_module.messagebox, "showinfo") as info,
        ):
            self.app.apply_clustering()
        self.assertTrue(seen["busy"])
        self.assertFalse(self.app._busy)
        self.assertFalse(any(isinstance(child, tk.Toplevel) for child in self.root.winfo_children()))
        info.assert_called_once()
        self.assertIn("disabled", self.app.apply_button.state())

    def test_apply_moves_after_confirmation(self):
        self.app.load_folder(self.folder)
        with patch.object(action_module.messagebox, "askyesno", return_value=False):
            self.app.apply_clustering()
        self.assertTrue((self.folder / PHOTOS[0]).is_file())

        with (
            patch.object(action_module.messagebox, "askyesno", return_value=True),
            patch.object(action_module.messagebox, "showinfo") as info,
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
        with patch.object(action_module.messagebox, "showinfo") as info:
            self.app.apply_clustering()
        self.assertEqual(info.call_args.args[0], "Nothing to move")

    def test_apply_reports_move_errors(self):
        self.app.load_folder(self.folder)
        with (
            patch.object(action_module.messagebox, "askyesno", return_value=True),
            patch.object(action_module.messagebox, "showerror") as error,
            patch.object(
                action_module, "move_into_cluster_folders", side_effect=OSError("disk full")
            ),
        ):
            self.app.apply_clustering()
        error.assert_called_once()
        self.assertTrue((self.folder / PHOTOS[0]).is_file())

    def test_flatten_restores_files_and_keeps_other_folders(self):
        self.app.load_folder(self.folder)
        with (
            patch.object(action_module.messagebox, "askyesno", return_value=True),
            patch.object(action_module.messagebox, "showinfo"),
        ):
            self.app.apply_clustering()
        with patch.object(action_module.messagebox, "askyesno", return_value=False):
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
            patch.object(action_module.messagebox, "askyesno", return_value=True),
            patch.object(action_module.messagebox, "showinfo") as info,
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
        with patch.object(action_module.messagebox, "showinfo") as nothing:
            self.app.flatten_clustering()
        nothing.assert_called_once()
        self.assertEqual(nothing.call_args.args[0], "Nothing to flatten")

        with (
            patch.object(action_module.messagebox, "askyesno", return_value=True),
            patch.object(action_module.messagebox, "showinfo"),
        ):
            self.app.apply_clustering()
        with (
            patch.object(action_module.messagebox, "askyesno", return_value=True),
            patch.object(action_module.messagebox, "showerror") as error,
            patch.object(action_module, "flatten_cluster_folders", side_effect=OSError("busy")),
        ):
            self.app.flatten_clustering()
        error.assert_called_once()
        self.assertEqual(len(self.app.overview.bars), 2)

    def test_choosing_another_folder_replaces_the_preview(self):
        self.app.load_folder(self.folder)
        with (
            patch.object(action_module.messagebox, "askyesno", return_value=True),
            patch.object(action_module.messagebox, "showinfo"),
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
        with patch.object(action_module.messagebox, "askyesno") as ask:
            self.app.flatten_clustering()
        ask.assert_not_called()

    def test_apply_without_folder_does_nothing(self):
        with patch.object(action_module.messagebox, "askyesno") as ask:
            self.app.apply_clustering()
        ask.assert_not_called()

class MainTests(unittest.TestCase):
    def test_main_builds_the_app_and_runs_the_loop(self):
        root = make_root()
        with (
            patch.object(app_module.tk, "Tk", return_value=root),
            patch.object(root, "mainloop") as loop,
        ):
            self.assertEqual(app_module.main(), 0)
        loop.assert_called_once()
        self.assertEqual(root.state(), "withdrawn")
        root.destroy()

