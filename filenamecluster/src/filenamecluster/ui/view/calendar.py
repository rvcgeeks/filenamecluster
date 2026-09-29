"""Month calendar where every day of an event is coloured by its cluster.

Author: Rajas Chavadekar (rvchavadekar@gmail.com). Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import sys
from filenamecluster.log import trace_module

import calendar
import tkinter as tk
from datetime import date
from tkinter import ttk
from typing import Callable, Sequence

from . import theme

PHOTO_FILLS = ("#aed6f1", "#7fb9e6")
SPAN_FILL = "#e3f0fa"
OUTSIDE_FILL = "#f5f9fd"
HEADER_HEIGHT = 24


def month_weeks(year: int, month: int) -> list[list[date]]:
    """Weeks of the month, Monday first, padded with neighbouring days."""

    return calendar.Calendar(firstweekday=0).monthdatescalendar(year, month)


def shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    index = year * 12 + (month - 1) + delta
    return index // 12, index % 12 + 1


class CalendarView(ttk.Frame):
    """One month at a time. Clicking a day calls ``on_day(date)``.

    A double-click on the orange or yellow selection calls ``on_open(index)``.
    """

    def __init__(
        self,
        master: tk.Misc,
        *,
        on_day: Callable[[date], None] | None = None,
        on_open: Callable[[int], None] | None = None,
        translate: Callable[..., str],
        fonts: dict | None = None,
    ) -> None:
        super().__init__(master)
        self.clusters: tuple = ()
        self.days: dict[date, object] = {}
        today = date.today()
        self.year, self.month = today.year, today.month
        self.selected_day: date | None = None
        self.selected_cluster: int | None = None
        self._on_day = on_day
        self._on_open = on_open
        self._translate = translate
        fonts = fonts or {}
        self._small = fonts.get("small")
        self._bold = fonts.get("bold")
        self._cells: dict[date, tuple[float, float, float, float]] = {}

        nav = ttk.Frame(self)
        nav.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        ttk.Button(nav, text="◀◀", width=4, command=self.previous_event_month).pack(side="left")
        ttk.Button(nav, text="◀", width=3, command=lambda: self.move(-1)).pack(
            side="left", padx=(4, 0)
        )
        ttk.Button(nav, text="▶▶", width=4, command=self.next_event_month).pack(side="right")
        ttk.Button(nav, text="▶", width=3, command=lambda: self.move(1)).pack(
            side="right", padx=(0, 4)
        )
        self.title = ttk.Label(nav, anchor="center", style="Info.TLabel")
        self.title.pack(side="left", fill="x", expand=True)

        self.canvas = tk.Canvas(
            self,
            width=theme.px(420),
            height=theme.px(300),
            background=theme.SURFACE,
            highlightthickness=1,
            highlightbackground=theme.BORDER,
        )
        self.canvas.grid(row=1, column=0, sticky="nsew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.canvas.bind("<Configure>", lambda event: self.redraw())
        self.canvas.bind("<Button-1>", self._clicked)
        self.canvas.bind("<Double-Button-1>", self._double)
        self.redraw()

    def set_clusters(self, clusters: Sequence, days: dict[date, object]) -> None:
        self.clusters = tuple(clusters)
        self.days = dict(days)
        self.selected_cluster = None
        self.selected_day = None
        if self.clusters:
            first = self.clusters[0].start
            self.year, self.month = first.year, first.month
        self.redraw()

    def show_month(self, year: int, month: int) -> None:
        self.year, self.month = year, month
        self.redraw()

    def move(self, delta: int) -> None:
        self.show_month(*shift_month(self.year, self.month, delta))

    def select_day(self, day: date | None) -> None:
        self.selected_day = day
        if day is not None:
            self.year, self.month = day.year, day.month
        self.redraw()

    def select_cluster(self, index: int | None) -> None:
        self.selected_cluster = index
        self.redraw()

    def event_months(self) -> list[tuple[int, int]]:
        return sorted({(day.year, day.month) for day in self.days})

    def previous_event_month(self) -> None:
        earlier = [m for m in self.event_months() if m < (self.year, self.month)]
        if earlier:
            self.show_month(*earlier[-1])

    def next_event_month(self) -> None:
        later = [m for m in self.event_months() if m > (self.year, self.month)]
        if later:
            self.show_month(*later[0])

    def day_at(self, x: float, y: float) -> date | None:
        for day, (x0, y0, x1, y1) in self._cells.items():
            if x0 <= x < x1 and y0 <= y < y1:
                return day
        return None

    def redraw(self) -> None:
        canvas = self.canvas
        canvas.delete("all")
        self._cells = {}
        self.title.configure(
            text=f"{self._translate(f'month_{self.month}')} {self.year}"
        )
        header = theme.px(HEADER_HEIGHT)
        width = max(canvas.winfo_width(), theme.px(420))
        height = max(canvas.winfo_height(), theme.px(300))
        weeks = month_weeks(self.year, self.month)
        cell_w = width / 7
        cell_h = (height - header) / len(weeks)

        for column in range(7):
            canvas.create_text(
                column * cell_w + cell_w / 2,
                header / 2,
                text=self._translate(f"wd_short_{column}"),
                fill=theme.MUTED,
                font=self._small,
            )

        for row, week in enumerate(weeks):
            for column, day in enumerate(week):
                box = (
                    column * cell_w,
                    header + row * cell_h,
                    (column + 1) * cell_w,
                    header + (row + 1) * cell_h,
                )
                self._cells[day] = box
                self._draw_cell(day, box)

    def _draw_cell(self, day: date, box: tuple[float, float, float, float]) -> None:
        x0, y0, x1, y1 = box
        info = self.days.get(day)
        in_month = day.month == self.month
        if info is None:
            fill = theme.SURFACE if in_month else OUTSIDE_FILL
        elif info.cluster == self.selected_cluster:
            fill = theme.SELECTED_FILL if info.files else "#fbe3bd"
        elif info.files:
            fill = PHOTO_FILLS[(self.clusters[info.cluster].number) % 2]
        else:
            fill = SPAN_FILL
        chosen = day == self.selected_day
        self.canvas.create_rectangle(
            x0 + 1,
            y0 + 1,
            x1 - 1,
            y1 - 1,
            fill=fill,
            outline=theme.SELECTED_OUTLINE if chosen else theme.GRID_MINOR,
            width=3 if chosen else 1,
        )
        self.canvas.create_text(
            x0 + theme.px(6),
            y0 + theme.px(5),
            anchor="nw",
            text=str(day.day),
            fill=theme.TEXT if in_month else theme.BORDER,
            font=self._bold if info and info.files else self._small,
        )
        if info is None:
            return
        number = self.clusters[info.cluster].number
        self.canvas.create_text(
            x1 - theme.px(5),
            y0 + theme.px(5),
            anchor="ne",
            text=f"#{number}",
            fill=theme.ACCENT_ACTIVE,
            font=self._small,
        )
        if info.files:
            self.canvas.create_text(
                x0 + theme.px(6),
                y1 - theme.px(5),
                anchor="sw",
                text=self._translate(
                    "file_one" if info.files == 1 else "file_many",
                    n=info.files,
                ),
                fill=theme.TEXT,
                font=self._small,
            )

    def _clicked(self, event: tk.Event) -> None:
        day = self.day_at(event.x, event.y)
        if day is not None and self._on_day:
            self._on_day(day)

    def _double(self, event: tk.Event) -> None:
        """Open the folder for the orange or yellow selection."""

        day = self.day_at(event.x, event.y)
        if day is None or self._on_open is None:
            return
        info = self.days.get(day)
        if info is None or info.cluster is None or info.cluster != self.selected_cluster:
            return
        self._on_open(info.cluster)

trace_module(sys.modules[__name__])
