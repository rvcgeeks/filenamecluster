"""TimelineView: zoom, fit, scroll, and clicks."""

from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from conftest import WindowCase


class TimelineTests(WindowCase):
    ALBUM = False
    LOAD = True

    def test_timeline_zoom_fit_scroll_and_clicks(self):
        view = self.app.view.overview
        before = view.scale.pixels_per_day
        view.zoom_in()
        self.assertGreater(view.scale.pixels_per_day, before)
        view.zoom_out()
        self.assertAlmostEqual(view.scale.pixels_per_day, before)
        view._zoom_wheel(SimpleNamespace(delta=120, x=10))
        view._zoom_wheel(SimpleNamespace(delta=-120, x=10))
        self.assertEqual(view._wheel(SimpleNamespace(delta=1)), "break")
        self.assertEqual(view._wheel(SimpleNamespace(delta=-1)), "break")
        view.fit()
        self.assertIn("=", view.scale_label.cget("text"))

        bar = view.bars[1]
        with patch.object(view.canvas, "gettags", return_value=("current", "bar", "c1", "rect")):
            view._clicked(SimpleNamespace(x=bar.x0 + 1, y=0))
        self.assertEqual(self.app.model.selected_cluster, 1)
        view.canvas.xview_moveto(0)
        offset = view.canvas.canvasx(0)
        with patch.object(view.canvas, "gettags", return_value=()):
            view._clicked(SimpleNamespace(x=view.bars[0].x0 + 1 - offset, y=0))
        self.assertEqual(self.app.model.selected_day, date(2024, 1, 1))

        view.show(())
        view.zoom_in()
        view.fit()
        view._clicked(SimpleNamespace(x=0, y=0))
        self.assertIsNone(view.scale)
