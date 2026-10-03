"""JSON language catalogs share one key set, and English keeps the app's phrases."""

import unittest

from filenamecluster.ui.model import LearnedKind, LearnedSummary
from filenamecluster.ui.view import CATALOGS, describe_model, t


class CatalogTests(unittest.TestCase):
    def test_json_catalogs_match_english(self):
        english = CATALOGS["en"]
        self.assertEqual(set(CATALOGS), {"en", "hi", "mr", "de", "fr", "ja", "ko"})
        for catalog in CATALOGS.values():
            self.assertEqual(set(catalog), set(english))
            self.assertTrue(all(value.strip() for value in catalog.values()))
        self.assertEqual(t("apply"), "Apply clustering")
        self.assertEqual(t("flatten"), "Flatten clustering")
        self.assertIn("filenamecluster-model.json", t("about_options_body"))
        self.assertIn("timestamps only", t("about_options_body"))
        self.assertIn("options", t("about_options_body"))
        self.assertIn("finditer", t("about_regex_body").format())
        self.assertIn("(?P<y>", t("about_regex_camera_body").format())
        self.assertIn("CamScanner", t("about_regex_scan_body").format())
        self.assertIn("{path}", CATALOGS["en"]["about_logging_body"])
        self.assertNotEqual(t("apply", code="hi"), "Apply clustering")
        self.assertEqual(t("choose_folder"), "Storage folder…")

    def test_the_status_line_describes_the_learned_boundary(self):
        none = LearnedSummary(LearnedKind.NONE)
        self.assertEqual(
            describe_model(none),
            t("model_none", name="filenamecluster-model.json"),
        )
        one_rhythm = LearnedSummary(LearnedKind.ONE_GROUP)
        self.assertEqual(describe_model(one_rhythm), t("model_one", name="filenamecluster-model.json"))
        learned = LearnedSummary(LearnedKind.BOUNDARY, 12.4)
        self.assertEqual(
            describe_model(learned),
            t("model_learned", hours="12", name="filenamecluster-model.json"),
        )
