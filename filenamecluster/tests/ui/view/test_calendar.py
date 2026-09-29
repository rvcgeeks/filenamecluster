"""Calendar month geometry, navigation, and clicks."""

import unittest
from datetime import date

from types import SimpleNamespace
from unittest.mock import patch

from filenamecluster.ui.view import month_weeks, shift_month
from conftest import WindowCase

class CalendarDataTests(unittest.TestCase):
    def test_month_helpers(self):
        weeks = month_weeks(2024, 2)
        self.assertEqual(weeks[0][0], date(2024, 1, 29))
        self.assertTrue(all(len(week) == 7 for week in weeks))
        self.assertEqual(shift_month(2024, 12, 1), (2025, 1))
        self.assertEqual(shift_month(2024, 1, -1), (2023, 12))


class CalendarWidgetTests(WindowCase):
    ALBUM = False
    LOAD = True

    def test_calendar_navigation_and_clicks(self):
        calendar = self.app.view.calendar
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
        self.assertEqual(self.app.model.selected_day, date(2024, 1, 20))
        self.assertEqual(self.app.model.selected_cluster, 1)
        self.assertIsNone(calendar.day_at(-5, -5))
        calendar._clicked(SimpleNamespace(x=-5, y=-5))

        day_view = self.app.view.day_view
        with patch.object(day_view.canvas, "gettags", return_value=("bar", "c1")):
            day_view._clicked(SimpleNamespace(x=day_view.bars[0].x0, y=0))
        self.assertEqual(self.app.model.selected_cluster, 1)
        with patch.object(day_view.canvas, "gettags", return_value=()):
            day_view._clicked(SimpleNamespace(x=0, y=0))
