"""JSON language catalogs share one key set, and English keeps the app's phrases."""

import unittest

from filenamecluster.ui.i18n import CATALOGS, set_language, t


class CatalogTests(unittest.TestCase):
    def tearDown(self):
        set_language("en")

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
        set_language("hi")
        self.assertNotEqual(t("apply"), "Apply clustering")
        set_language("en")
        self.assertEqual(t("choose_folder"), "Choose folder…")
