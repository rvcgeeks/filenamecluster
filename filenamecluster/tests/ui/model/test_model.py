"""Window session state. Clustering decisions stay in core."""

import unittest
from datetime import date, datetime

from filenamecluster.core import ClusterParams, ClusterResult, NamedCluster, TimestampedFile
from filenamecluster.ui.model import AppModel, ChooseStatus, Topic


class SessionTests(unittest.TestCase):
    def test_a_new_session_has_no_folder_and_no_selection(self):
        model = AppModel()
        self.assertIsNone(model.directory)
        self.assertIsNone(model.result)
        self.assertIsNone(model.selected_cluster)
        self.assertIsNone(model.selected_day)
        self.assertEqual(model.files_by_day, {})
        self.assertGreater(float(model.option_text["floor"]), 0)
        self.assertEqual(model.language, "en")
        self.assertFalse(model.logging_enabled)
        self.assertFalse(model.busy)
        self.assertIsInstance(model.status, ChooseStatus)
        drafts = model.option_drafts()
        drafts["floor"] = "nope"
        self.assertNotEqual(model.option_text["floor"], "nope")

    def test_a_preview_indexes_files_by_the_day_they_were_taken(self):
        model = AppModel()
        model.set_selection(0, date(2024, 1, 1))
        model.remember_preview(
            ClusterResult(
                clusters=(),
                ignored_without_timestamp=(),
                ignored_directories=(),
                params=ClusterParams(),
            )
        )
        self.assertIsNone(model.selected_cluster)
        self.assertIsNone(model.selected_day)
        self.assertEqual(model.files_by_day, {})

    def test_a_day_belongs_to_the_event_that_covers_it(self):
        model = AppModel()
        item = TimestampedFile("a.jpg", datetime(2024, 1, 1, 10))
        model.remember_preview(ClusterResult(
            clusters=(NamedCluster(1, "event", (item,)),),
            ignored_without_timestamp=(),
            ignored_directories=(),
            params=ClusterParams(),
        ))
        self.assertEqual(model.cluster_on_day(date(2024, 1, 1)), 0)
        self.assertIsNone(model.cluster_on_day(date(2024, 2, 1)))

    def test_a_built_in_description_is_dirty_only_when_its_wording_changes(self):
        model = AppModel()
        row = model.rows[0]
        model.update_cell(row.iid, "description", row.description)
        self.assertFalse(model.rows[0].dirty)
        model.update_cell(row.iid, "description", "My own name")
        self.assertTrue(model.rows[0].dirty)
        self.assertEqual(model.rows[0].description, "My own name")

    def test_sort_toggles_on_the_single_model(self):
        model = AppModel()
        seen = []
        model.listen(seen.append)
        self.assertEqual(model.toggle_sort("files"), ("files", False))
        self.assertEqual(model.toggle_sort("files"), ("files", True))
        self.assertEqual(model.toggle_sort("number"), ("number", False))
        self.assertEqual(seen, [Topic.SORT, Topic.SORT, Topic.SORT])
