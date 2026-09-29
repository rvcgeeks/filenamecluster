"""AppView: switching language redraws the window."""


from filenamecluster.ui.view import t
from conftest import WindowCase


class LanguageTests(WindowCase):
    ALBUM = False
    LOAD = True

    def test_language_switches_and_english_returns(self):
        self.assertEqual(self.app.view.apply_button.cget("text"), "Apply clustering")
        self.app.view.language_var.set("Deutsch")
        self.app.view._on_language()
        self.assertEqual(
            self.app.view.pattern_tree.set("date_only", "description"),
            t("pattern_date_only", code="de"),
        )
        self.assertEqual(
            self.app.view.model_tree.heading("meaning")["text"],
            t("col_meaning", code="de"),
        )
        self.assertEqual(
            self.app.view.model_tree.set("boundary_hours", "meaning"),
            t("model_boundary", code="de"),
        )
        self.assertEqual(
            self.app.view.apply_button.cget("text"),
            t("apply", code="de"),
        )
        self.assertNotEqual(self.app.view.apply_button.cget("text"), "Apply clustering")
        self.app.view.language_var.set("English")
        self.app.view._on_language()
        self.assertEqual(self.app.view.pattern_tree.set("date_only", "description"), "Date only")
        self.assertEqual(self.app.view.apply_button.cget("text"), "Apply clustering")
        self.assertIn("Flatten clustering", self.app.view.about_text.get("1.0", "end"))
