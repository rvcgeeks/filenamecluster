"""InfoTabs: the Skipped list and the read-only About text."""

from filenamecluster.ui.model import SkippedReason
from filenamecluster.ui.view import sections, t
from conftest import WindowCase


class InfoTabTests(WindowCase):
    def test_skipped_lists_folders_and_files_with_reasons(self):
        view = self.app.view
        view.show_skipped(
            (
                ("album", SkippedReason.SUBFOLDER),
                ("event-1", SkippedReason.EVENT_FOLDER),
            ),
            (("notes.txt", SkippedReason.NO_TIMESTAMP),),
        )
        rows = [view.skipped_tree.item(iid, "values") for iid in view.skipped_tree.get_children()]
        self.assertEqual(
            [tuple(row) for row in rows],
            [
                ("album", t("reason_subfolder")),
                ("event-1", t("reason_event")),
                ("notes.txt", t("reason_no_timestamp")),
            ],
        )

    def test_about_shows_every_section_and_stays_read_only(self):
        text = self.app.view.about_text
        body = text.get("1.0", "end")
        for heading, _body in sections():
            self.assertIn(heading, body)
        self.assertEqual(str(text.cget("state")), "disabled")
