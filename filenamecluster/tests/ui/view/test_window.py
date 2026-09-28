"""Widget behaviour for the timeline, the calendar, and the language menu."""

import tkinter as tk
import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from filenamecluster.ui.app import FileNameClusterApp
from filenamecluster.ui.model.i18n import set_language, t
from filenamecluster.ui.view import theme

PHOTOS = (
    "IMG_20240101_100000.jpg",
    "IMG_20240101_110000.jpg",
    "IMG_20240102_090000.jpg",
    "IMG_20240120_080000.jpg",
    "notes.txt",
)


def make_root() -> tk.Tk:
    """A Tk interpreter whose window stays withdrawn for the whole test.

    Creating ``Tk`` can map a window before Python runs the next line, so this
    withdraws it immediately and ignores later requests to show, zoom, or fill
    the screen. Tests still build the real widgets. They do not present them.
    """

    try:
        root = tk.Tk()
    except tk.TclError as exc:
        raise unittest.SkipTest(f"no display for Tk: {exc}")
    root.withdraw()
    real_attributes = root.attributes
    real_state = root.state

    def attributes(*args):
        if len(args) >= 2 and args[0] == "-fullscreen" and args[1]:
            return ""
        return real_attributes(*args)

    def state(value=None):
        if value is None:
            return real_state()
        if value != "withdrawn":
            return real_state()
        return real_state(value)

    root.attributes = attributes
    root.state = state
    root.deiconify = lambda: None
    root.withdraw()
    return root

class WidgetTests(unittest.TestCase):
    def setUp(self):
        set_language("en")
        self.root = make_root()
        self.app = FileNameClusterApp(self.root)
        self.tmp = TemporaryDirectory()
        folder = Path(self.tmp.name)
        for name in PHOTOS:
            (folder / name).write_bytes(b"x")
        self.app.load_folder(folder)
        self.root.update_idletasks()

    def tearDown(self):
        set_language("en")
        theme.use_script(self.root, self.app.fonts, "en")
        self.assertEqual(self.root.state(), "withdrawn")
        self.root.destroy()
        self.tmp.cleanup()

    def test_timeline_zoom_fit_scroll_and_clicks(self):
        view = self.app.overview
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
        self.assertEqual(self.app.selected_cluster, 1)
        view.canvas.xview_moveto(0)
        offset = view.canvas.canvasx(0)
        with patch.object(view.canvas, "gettags", return_value=()):
            view._clicked(SimpleNamespace(x=view.bars[0].x0 + 1 - offset, y=0))
        self.assertEqual(self.app.selected_day, date(2024, 1, 1))

        view.show(())
        view.zoom_in()
        view.fit()
        view._clicked(SimpleNamespace(x=0, y=0))
        self.assertIsNone(view.scale)

    def test_language_switches_and_english_returns(self):
        self.assertEqual(self.app.apply_button.cget("text"), "Apply clustering")
        self.app.language_var.set("Deutsch")
        self.app._language_changed()
        self.assertEqual(self.app.pattern_tree.set("date_only", "description"), t("pattern_date_only"))
        self.assertEqual(self.app.model_tree.heading("meaning")["text"], t("col_meaning"))
        self.assertEqual(self.app.model_tree.set("boundary_hours", "meaning"), t("model_boundary"))
        self.assertEqual(self.app.apply_button.cget("text"), t("apply"))
        self.assertNotEqual(self.app.apply_button.cget("text"), "Apply clustering")
        self.app.language_var.set("English")
        self.app._language_changed()
        self.assertEqual(self.app.pattern_tree.set("date_only", "description"), "Date only")
        self.assertEqual(self.app.apply_button.cget("text"), "Apply clustering")
        self.assertIn("Flatten clustering", self.app.about_text.get("1.0", "end"))

    def test_calendar_navigation_and_clicks(self):
        calendar = self.app.calendar
        self.assertEqual((calendar.year, calendar.month), (2024, 1))
        calendar.move(1)
        self.assertEqual((calendar.year, calendar.month), (2024, 2))
        calendar.previous_event_month()
        self.assertEqual((calendar.year, calendar.month), (2024, 1))
        calendar.previous_event_month()
        self.assertEqual((calendar.year, calendar.month), (2024, 1))
        calendar.show_month(2023, 5)
        calendar.next_event_month()
        self.assertEqual((calendar.year, calendar.month), (2024, 1))
        calendar.next_event_month()
        self.assertEqual((calendar.year, calendar.month), (2024, 1))

        x0, y0, x1, y1 = calendar._cells[date(2024, 1, 20)]
        calendar._clicked(SimpleNamespace(x=(x0 + x1) / 2, y=(y0 + y1) / 2))
        self.assertEqual(self.app.selected_day, date(2024, 1, 20))
        self.assertEqual(self.app.selected_cluster, 1)
        self.assertIsNone(calendar.day_at(-5, -5))
        calendar._clicked(SimpleNamespace(x=-5, y=-5))

        day_view = self.app.day_view
        with patch.object(day_view.canvas, "gettags", return_value=("bar", "c1")):
            day_view._clicked(SimpleNamespace(x=day_view.bars[0].x0, y=0))
        self.assertEqual(self.app.selected_cluster, 1)
        with patch.object(day_view.canvas, "gettags", return_value=()):
            day_view._clicked(SimpleNamespace(x=0, y=0))

