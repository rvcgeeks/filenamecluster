"""FolderPreviewing: preview the chosen folder, or say that none is chosen."""

from filenamecluster.ui.view import t
from conftest import WindowCase


class PreviewingTests(WindowCase):
    def test_refresh_without_a_folder_keeps_the_empty_status(self):
        self.app.controller.refresh()
        self.assertEqual(self.app.view.status_text.get(), t("choose_status"))
        self.assertIsNone(self.app.model.result)
