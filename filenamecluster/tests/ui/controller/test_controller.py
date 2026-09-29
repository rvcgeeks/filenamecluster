"""AppController: choose a folder, preview it, keep one selection, and save options."""

import json
from datetime import date
from unittest.mock import patch

from filenamecluster.ui.controller import AppController, Wait
from filenamecluster.ui.view import Dialogs, t
from conftest import PHOTOS, WindowCase


class ControllerTests(WindowCase):
    def test_choosing_a_folder_previews_without_moving(self):
        with patch.object(Dialogs._filedialog, "askdirectory", return_value=str(self.folder)):
            self.app.controller.choose_folder()
        result = self.app.model.result
        self.assertEqual(len(result.clusters), 2)
        self.assertEqual(result.file_count, 4)
        self.assertEqual(len(self.app.view.cluster_tree.get_children()), 2)
        self.assertEqual(len(self.app.view.skipped_tree.get_children()), 2)
        self.assertEqual(len(self.app.view.overview.bars), 2)
        self.assertEqual(self.app.model.selected_day, date(2024, 1, 1))
        self.assertEqual(len(self.app.view.day_tree.get_children()), 2)
        self.assertIn("2 events", self.app.view.status_text.get())
        self.assertNotIn("disabled", self.app.view.apply_button.state())
        self.assertIn("disabled", self.app.view.flatten_button.state())
        self.assertTrue((self.folder / PHOTOS[0]).is_file())

        with patch.object(Dialogs._filedialog, "askdirectory", return_value=""):
            self.app.controller.choose_folder()
        self.assertEqual(self.app.model.directory, self.folder)

    def test_choosing_another_folder_replaces_the_preview(self):
        self.app.controller.load_folder(self.folder)
        with (
            patch.object(Dialogs._messagebox, "askyesno", return_value=True),
            patch.object(Dialogs._messagebox, "showinfo"),
        ):
            self.app.controller.apply_clustering()
        self.assertEqual(len(self.app.view.overview.bars), 2)
        other = self.folder / "next"
        other.mkdir()
        (other / "IMG_20240201_100000.jpg").write_bytes(b"z")
        self.app.controller.load_folder(other)
        self.assertEqual(len(self.app.model.result.clusters), 1)
        self.assertEqual(self.app.model.result.clusters[0].files[0].name, "IMG_20240201_100000.jpg")

    def test_unreadable_folder_is_reported(self):
        self.app.controller.load_folder(self.folder / "missing")
        self.assertIn("Could not read", self.app.view.status_text.get())

    def test_selecting_clusters_and_days_syncs_every_view(self):
        self.app.controller.load_folder(self.folder)
        self.app.controller.select_cluster(1)
        self.assertEqual(self.app.model.selected_cluster, 1)
        self.assertEqual(self.app.view.overview.selected, 1)
        self.assertEqual(self.app.view.calendar.selected_cluster, 1)
        self.assertEqual(self.app.view.cluster_tree.selection(), ("1",))
        self.assertEqual(self.app.model.selected_day, date(2024, 1, 20))
        self.app.controller.select_cluster(99)
        self.assertEqual(self.app.model.selected_cluster, 1)

        self.app.view.cluster_tree.selection_set("0")
        self.app.view._on_cluster_selected()
        self.assertEqual(self.app.model.selected_cluster, 0)

        self.app.controller.day_chosen(date(2024, 1, 2))
        self.assertEqual(self.app.model.selected_day, date(2024, 1, 2))
        self.assertEqual(len(self.app.view.day_tree.get_children()), 1)
        self.app.controller.day_chosen(date(2024, 1, 10))
        self.assertEqual(len(self.app.view.day_tree.get_children()), 0)
        self.assertEqual(self.app.model.selected_cluster, 0)

        self.app.controller.day_chosen(date(2024, 1, 20))
        self.assertEqual(self.app.model.selected_cluster, 1)

    def test_every_wait_says_why_before_and_after_confirmation(self):
        keys: list[str] = []
        original = AppController._run_disk

        def wrapped(controller, message_key, work, on_done):
            keys.append(message_key)
            return original(controller, message_key, work, on_done)

        with patch.object(AppController, "_run_disk", wrapped):
            self.app.controller.load_folder(self.folder)
            self.app.controller.refresh()
        self.assertEqual(keys, [Wait.OPEN, Wait.PREVIEW])

        keys.clear()
        with (
            patch.object(AppController, "_run_disk", wrapped),
            patch.object(Dialogs._messagebox, "askyesno", return_value=True),
            patch.object(Dialogs._messagebox, "showinfo"),
        ):
            self.app.controller.apply_clustering()
        self.assertEqual(keys, [Wait.APPLY_CHECK, Wait.APPLY])

        keys.clear()
        with (
            patch.object(AppController, "_run_disk", wrapped),
            patch.object(Dialogs._messagebox, "askyesno", return_value=True),
            patch.object(Dialogs._messagebox, "showinfo"),
        ):
            self.app.controller.flatten_clustering()
        self.assertEqual(keys, [Wait.FLATTEN_CHECK, Wait.FLATTEN, Wait.AFTER_FLATTEN])
        for key in ("busy_open", "busy_preview", "busy_apply_check", "busy_apply",
                    "busy_flatten_check", "busy_flatten", "busy_after_flatten", "busy_after_error"):
            self.assertNotEqual(t(key), key)
        self.assertIn("No clusters", t("busy_flatten_check"))

    def test_saved_options_override_defaults_and_keep_learned(self):
        self.app.controller.load_folder(self.folder)
        path = self.folder / "filenamecluster-model.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        self.assertIsNone(raw["learned"])
        self.assertEqual(raw["options"]["floor_hours"], 3)
        self.assertIn("rules", raw["options"])
        raw["options"]["floor_hours"] = 2
        raw["options"]["ceiling_hours"] = 3
        path.write_text(json.dumps(raw), encoding="utf-8")
        self.app.view.option_vars["floor"].set(3)
        self.app.view.option_vars["ceiling"].set(720)
        self.app.controller.load_folder(self.folder)
        self.assertEqual(self.app.view.option_vars["floor"].get(), "2.0")
        self.assertEqual(self.app.view.option_vars["ceiling"].get(), "3.0")
        self.assertEqual(len(self.app.model.result.clusters), 3)
        again = json.loads(path.read_text(encoding="utf-8"))
        self.assertIsNone(again["learned"])
        self.assertEqual(again["options"]["floor_hours"], 2)
        self.assertEqual(again["options"]["ceiling_hours"], 3)

        again["options"] = {"floor_hours": "nope"}
        path.write_text(json.dumps(again), encoding="utf-8")
        self.app.controller.load_folder(self.folder)
        self.assertEqual(self.app.view.option_vars["floor"].get(), "3.0")
        self.assertEqual(len(self.app.model.result.clusters), 2)
        restored = json.loads(path.read_text(encoding="utf-8"))
        self.assertIsNone(restored["learned"])
        self.assertEqual(restored["options"]["floor_hours"], 3)

    def test_tighter_options_split_more(self):
        self.app.controller.load_folder(self.folder)
        self.app.view.option_vars["floor"].set(2)
        self.app.view.option_vars["ceiling"].set(3)
        self.app.controller.refresh()
        self.assertEqual(len(self.app.model.result.clusters), 3)

    def test_model_file_is_visible_and_holds_only_the_learned_boundary(self):
        self.app.controller.load_folder(self.folder)
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
