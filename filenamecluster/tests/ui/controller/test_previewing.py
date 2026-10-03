"""FolderPreviewing: preview the chosen folder, or say that none is chosen."""

from unittest.mock import patch

from filenamecluster.ui.view import Dialogs, t
from conftest import WindowCase


class PreviewingTests(WindowCase):
    def test_refresh_without_a_folder_keeps_the_empty_status(self):
        self.app.controller.refresh()
        self.assertEqual(self.app.view.status_text.get(), t("choose_status"))
        self.assertIsNone(self.app.model.result)

    def test_apply_reuses_a_fresh_preview(self):
        self.app.controller.load_folder(self.folder)
        with (
            patch("filenamecluster.core.operations.preview.cluster_directory") as cluster,
            patch.object(Dialogs._messagebox, "askyesno", return_value=True),
            patch.object(Dialogs._messagebox, "showinfo"),
        ):
            self.app.controller.apply_clustering()
        cluster.assert_not_called()
