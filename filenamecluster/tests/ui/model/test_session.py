"""Window session state. Clustering decisions stay in core."""

import unittest
from datetime import timedelta
from types import SimpleNamespace

from filenamecluster.ui.model.i18n import set_language, t
from filenamecluster.ui.model.session import AppModel, describe_model, hours


class SessionTests(unittest.TestCase):
    def tearDown(self):
        set_language("en")

    def test_hours_are_the_length_of_a_pause(self):
        self.assertEqual(hours(timedelta(hours=3)), 3)
        self.assertEqual(hours(timedelta(days=30)), 720)

    def test_the_status_line_describes_the_learned_boundary(self):
        set_language("en")
        self.assertEqual(describe_model(None), t("model_none", name="filenamecluster-model.json"))
        one_rhythm = SimpleNamespace(separated=False)
        self.assertEqual(describe_model(one_rhythm), t("model_one", name="filenamecluster-model.json"))
        learned = SimpleNamespace(separated=True, boundary_hours=12.4)
        self.assertEqual(
            describe_model(learned),
            t("model_learned", hours="12", name="filenamecluster-model.json"),
        )

    def test_a_new_session_has_no_folder_and_no_selection(self):
        model = AppModel()
        self.assertIsNone(model.directory)
        self.assertIsNone(model.result)
        self.assertIsNone(model.selected_cluster)
        self.assertIsNone(model.selected_day)
        self.assertEqual(model.files_by_day, {})
        self.assertIsNone(model.cluster_sort)
        self.assertEqual(model.pattern_desc_dirty, set())
        self.assertEqual(model.custom_pattern_seq, 1)
        text, failed = model.status_builder()
        self.assertEqual(text, t("choose_status"))
        self.assertFalse(failed)
