"""The window draws each session topic, and drawing does not write back."""

from datetime import date

from filenamecluster.log import logging_enabled, set_logging_enabled
from conftest import WindowCase


class SessionDrawTests(WindowCase):
    def tearDown(self):
        set_logging_enabled(False)
        super().tearDown()

    def test_opening_draws_every_pattern_row(self):
        rows = self.app.view.pattern_tree.get_children()
        self.assertEqual(len(rows), len(self.app.model.rows))
        self.assertEqual(self.app.view.pattern_tree.set(rows[0], "pattern"), self.app.model.rows[0].pattern)

    def test_folder_language_and_logging_follow_the_session(self):
        self.app.model.set_directory(self.folder)
        self.assertEqual(self.app.view.folder_text.get(), str(self.folder))
        self.app.controller.language_chosen("de")
        self.assertEqual(self.app.view.language_code(), "de")
        self.app.controller.logging_chosen(True)
        self.assertTrue(self.app.model.logging_enabled)
        self.assertTrue(logging_enabled())
        self.assertTrue(self.app.view.logging_var.get())
        self.app.controller.logging_chosen(False)
        self.assertFalse(logging_enabled())

    def test_an_invalid_row_is_painted_marked(self):
        self.app.controller.load_folder(self.folder)
        self.app.controller.pattern_committed("clock_separated", "pattern", "(")
        self.assertTrue(self.app.view.pattern_marked("clock_separated"))
        self.assertFalse(self.app.view.pattern_marked("clock_compact_sep"))

    def test_selection_without_a_preview_draws_no_day(self):
        self.app.model.set_selection(0, date(2024, 1, 1))
        self.assertEqual(self.app.view.day_tree.get_children(), ())
