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
