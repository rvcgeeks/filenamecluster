"""View forwards draw and dialog calls to the section that owns them."""

from conftest import WindowCase


class ForwardingTests(WindowCase):
    def test_the_window_forwards_a_cleared_day_and_its_status(self):
        view = self.app.view
        view.clear_day()
        self.assertEqual(view.day_tree.get_children(), ())
        view.paint_status(self.app.model.status)
        self.assertTrue(view.status_text.get())
