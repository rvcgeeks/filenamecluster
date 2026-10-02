"""ClustersTab: the cluster list sorts and keeps its arrow."""


from filenamecluster.ui.view import t
from conftest import WindowCase


class ClusterListTests(WindowCase):
    def test_cluster_list_sorts_by_number_and_file_count(self):
        self.app.controller.load_folder(self.folder)
        tree = self.app.view.cluster_tree
        counts = [int(tree.set(iid, "files")) for iid in tree.get_children()]
        self.assertGreater(max(counts), min(counts))
        self.assertEqual(tree.heading("number")["text"], "#")
        self.assertEqual(tree.heading("files")["text"], "Files")
        self.assertNotEqual(tree.heading("number")["command"], "")
        self.assertNotEqual(tree.heading("files")["command"], "")
        self.assertEqual(tree.heading("name")["command"], "")
        self.assertIn("major ones", self.app.view.about_text.get("1.0", "end"))

        self.app.controller.sort_clusters("files")
        self.assertEqual(tree.heading("files")["text"], "Files ↑")
        self.assertEqual(tree.heading("number")["text"], "#")
        ordered = [int(tree.set(iid, "files")) for iid in tree.get_children()]
        self.assertEqual(ordered, sorted(ordered))

        self.app.controller.sort_clusters("files")
        self.assertEqual(tree.heading("files")["text"], "Files ↓")
        ordered = [int(tree.set(iid, "files")) for iid in tree.get_children()]
        self.assertEqual(ordered, sorted(ordered, reverse=True))
        self.assertEqual(tree.get_children()[0], "0")

        self.app.controller.sort_clusters("number")
        self.assertEqual(tree.heading("number")["text"], "# ↑")
        self.assertEqual(tree.heading("files")["text"], "Files")
        numbers = [int(tree.set(iid, "number")) for iid in tree.get_children()]
        self.assertEqual(numbers, sorted(numbers))

        self.app.controller.sort_clusters("number")
        self.assertEqual(tree.heading("number")["text"], "# ↓")
        numbers = [int(tree.set(iid, "number")) for iid in tree.get_children()]
        self.assertEqual(numbers, sorted(numbers, reverse=True))

        tree.selection_set("0")
        self.app.view._on_cluster_selected()
        self.assertEqual(self.app.model.selected_cluster, 0)
        order = self.app.model.cluster_order()
        self.app.view.show_cluster_sort(order, self.app.model.selected_cluster, self.app.model.cluster_sort)
        self.assertEqual(tree.selection(), ("0",))

        self.app.controller.refresh()
        numbers = [int(tree.set(iid, "number")) for iid in tree.get_children()]
        self.assertEqual(numbers, sorted(numbers, reverse=True))
        self.assertEqual(tree.heading("number")["text"], "# ↓")

        self.app.view.language_var.set("Deutsch")
        self.app.view._on_language()
        self.assertTrue(tree.heading("number")["text"].endswith("↓"))
        self.assertIn(t("col_number"), tree.heading("number")["text"])


class FolderRenameTests(WindowCase):
    LOAD = True

    def test_rename_locks_the_original_stamp(self):
        from unittest.mock import patch

        from filenamecluster.ui.view.dialogs import Dialogs

        tree = self.app.view.cluster_tree
        iid = tree.get_children()[0]
        stamp = tree.set(iid, "name")
        editor = self.app.view.clusters.folder_names
        editor.begin(int(iid))
        self.assertEqual(editor.stamp.get(), stamp)
        self.assertIn("readonly", editor.stamp.state())
        editor.prefix.insert(0, "Trip")
        editor.suffix.insert(0, "evening")
        with patch.object(self.app.controller, "refresh") as refresh:
            editor.commit()
        refresh.assert_not_called()
        self.assertEqual(tree.set(iid, "name"), f"Trip {stamp} evening")

        event = type("Event", (), {"x": 1, "y": 1})()
        with (
            patch.object(tree, "identify_column", return_value="#2"),
            patch.object(tree, "identify_row", return_value=iid),
        ):
            editor._right_click(event)
        self.assertEqual(editor.stamp.get(), stamp)
        self.assertIn("readonly", editor.stamp.state())
        editor.close(save=False)

        editor.begin(int(iid))
        self.assertEqual(editor.prefix.get(), "Trip")
        self.assertEqual(editor.suffix.get(), "evening")
        self.assertEqual(editor.stamp.get(), stamp)
        self.assertIn("readonly", editor.stamp.state())
        editor.close(save=False)

        self.app.controller.load_folder(self.folder)
        editor.begin(int(iid))
        self.assertEqual(editor.stamp.get(), stamp)
        self.assertIn("readonly", editor.stamp.state())
        self.assertEqual(editor.prefix.get(), "Trip")
        editor.close(save=False)

        (self.folder / stamp).mkdir()
        editor.begin(int(iid))
        editor.prefix.delete(0, "end")
        editor.prefix.insert(0, "Goa")
        editor.suffix.delete(0, "end")
        editor.commit()
        self.assertTrue((self.folder / f"Goa {stamp}").is_dir())
        self.assertFalse((self.folder / stamp).exists())
        self.assertEqual(tree.set(str(int(iid)), "name"), f"Goa {stamp}")

        (self.folder / f"Taken {stamp}").mkdir()
        editor.begin(int(iid))
        editor.prefix.delete(0, "end")
        editor.prefix.insert(0, "Taken")
        with patch.object(Dialogs._messagebox, "showerror") as error:
            editor.commit()
        self.assertTrue(error.called)
        self.assertTrue((self.folder / f"Goa {stamp}").is_dir())

        editor.begin(int(iid))
        editor.prefix.delete(0, "end")
        editor.prefix.insert(0, "Bad/Name")
        with patch.object(Dialogs._messagebox, "showerror") as error:
            editor.commit()
        self.assertTrue(error.called)
        self.assertEqual(editor._frame, None)


class CloseStoreTests(WindowCase):
    LOAD = True

    def test_closing_stores_a_changed_option_and_leaves_an_unchanged_file(self):
        import json

        path = self.folder / "filenamecluster-model.json"
        before = path.read_bytes()
        self.app.controller.store_on_close()
        self.assertEqual(path.read_bytes(), before)

        self.app.model.set_option_text("floor", "4")
        real_destroy = self.root.destroy
        self.root.destroy = lambda: None
        try:
            self.app.view.close()
        finally:
            self.root.destroy = real_destroy
        raw = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(raw["options"]["floor_hours"], 4)
        self.assertEqual(raw["learned"], json.loads(before)["learned"])

        self.app.model.set_option_text("floor", "nope")
        self.app.controller.store_on_close()
        self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["options"]["floor_hours"], 4)
