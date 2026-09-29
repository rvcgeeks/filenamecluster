"""FolderPreview: saved options are used, left out, or ignored when a folder is chosen."""

import json

from conftest import WindowCase


class FolderPreviewTests(WindowCase):
    def saved(self):
        return self.folder / "filenamecluster-model.json"

    def rewrite(self, change):
        raw = json.loads(self.saved().read_text(encoding="utf-8"))
        change(raw["options"])
        self.saved().write_text(json.dumps(raw), encoding="utf-8")

    def test_first_choice_uses_the_built_in_options(self):
        self.app.controller.load_folder(self.folder)
        self.assertEqual(len(self.app.model.result.clusters), 2)
        self.assertTrue(self.saved().exists())

    def test_an_invalid_saved_rule_is_left_out_and_the_rest_are_kept(self):
        self.app.controller.load_folder(self.folder)

        def break_one(options):
            options["min_year"] = 2000
            options["rules"][0]["pattern"] = "("

        self.rewrite(break_one)
        self.app.controller.load_folder(self.folder)
        first = self.app.model.rows[0]
        self.assertEqual(first.pattern, "(")
        self.assertTrue(self.app.view.pattern_marked(first.iid))
        self.assertEqual(self.app.view.limit_vars["min_year"].get(), "2000")
        self.assertEqual(len(self.app.model.result.clusters), 2)
        saved = json.loads(self.saved().read_text(encoding="utf-8"))
        self.assertTrue(saved["options"]["rules"][0]["invalid"])

    def test_unusable_saved_numbers_fall_back_to_the_defaults(self):
        self.app.controller.load_folder(self.folder)
        self.rewrite(lambda options: options.update(floor_hours=-1, min_year=2000))
        self.app.controller.load_folder(self.folder)
        self.assertEqual(self.app.view.limit_vars["min_year"].get(), "1990")
        self.assertEqual(len(self.app.model.result.clusters), 2)
