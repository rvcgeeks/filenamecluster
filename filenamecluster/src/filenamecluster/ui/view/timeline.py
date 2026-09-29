"""Scrollable, zoomable, to-scale timeline drawn on a Tk canvas.

Author: Rajas Chavadekar (rvchavadekar@gmail.com). Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import sys
from filenamecluster.log import trace_module

import tkinter as tk
from datetime import datetime
from tkinter import ttk
from typing import Callable, Sequence

from . import theme
from .layout import Bar, TimeScale, fit_pixels_per_day
from .timeline_draw import TimelinePainter, describe_zoom

ZOOM_STEP = 1.5


class TimelineView(TimelinePainter, ttk.Frame):
    """Clusters as bars on a time axis, one file per tick underneath.

    Mouse wheel scrolls sideways; Ctrl or Cmd with the wheel zooms around the
    pointer. Clicking a bar calls ``on_select(index)``; clicking anywhere else
    calls ``on_time(datetime)``.
    """

    def __init__(
        self,
        master: tk.Misc,
        *,
        height: int = 150,
        min_pixels_per_day: float = 0.0,
        placeholder: str = "",
        on_select: Callable[[int], None] | None = None,
        on_time: Callable[[datetime], None] | None = None,
        on_open: Callable[[int], None] | None = None,
        translate: Callable[..., str],
        fonts: dict | None = None,
    ) -> None:
        super().__init__(master)
        self.clusters: tuple = ()
        self.range: tuple[datetime, datetime] | None = None
        self.scale: TimeScale | None = None
        self.bars: list[Bar] = []
        self.selected: int | None = None
        self._min_ppd = min_pixels_per_day
        self._placeholder = placeholder
        self._on_select = on_select
        self._on_time = on_time
        self._on_open = on_open
        self._translate = translate
        self._small = (fonts or {}).get("small")

        tools = ttk.Frame(self)
        tools.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        ttk.Button(tools, text="−", width=3, command=self.zoom_out).pack(side="left")
        ttk.Button(tools, text="+", width=3, command=self.zoom_in).pack(side="left", padx=4)
        self.fit_button = ttk.Button(
            tools,
            text=self._translate("fit"),
            command=self.fit,
        )
        self.fit_button.pack(side="left")
        self.scale_label = ttk.Label(tools, style="Muted.TLabel")
        self.scale_label.pack(side="right")

        self.canvas = tk.Canvas(
            self,
            height=theme.px(height),
            background=theme.SURFACE,
            highlightthickness=1,
            highlightbackground=theme.BORDER,
        )
        xbar = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        ybar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=xbar.set, yscrollcommand=ybar.set)
        self.canvas.grid(row=1, column=0, sticky="nsew")
        ybar.grid(row=1, column=1, sticky="ns")
        xbar.grid(row=2, column=0, sticky="ew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self.canvas.bind("<Button-1>", self._clicked)
        self.canvas.bind("<Double-Button-1>", self._double)
        self.canvas.bind("<MouseWheel>", self._wheel)
        self.canvas.bind("<Shift-MouseWheel>", self._wheel)
        self.canvas.bind("<Control-MouseWheel>", self._zoom_wheel)
        self.canvas.bind("<Button-4>", lambda event: self._scroll(-1))
        self.canvas.bind("<Button-5>", lambda event: self._scroll(1))
        try:
            self.canvas.bind("<Command-MouseWheel>", self._zoom_wheel)
        except tk.TclError:
            pass
        self._draw_placeholder()

    def show(
        self,
        clusters: Sequence,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> None:
        """Draw ``clusters`` between ``start`` and ``end`` (default: all of them)."""

        self.clusters = tuple(clusters)
        self.selected = None
        if start is None or end is None:
            if not self.clusters:
                self.range = None
                self.scale = None
                self.bars = []
                self._draw_placeholder()
                return
            start = start or self.clusters[0].start
            end = end or self.clusters[-1].end
        self.range = (start, end)
        fit = fit_pixels_per_day(start, end, self._visible_width())
        self._draw(max(fit, self._min_ppd))
        self.canvas.xview_moveto(0)

    def zoom_in(self) -> None:
        self.zoom(ZOOM_STEP)

    def zoom_out(self) -> None:
        self.zoom(1 / ZOOM_STEP)

    def zoom(self, factor: float, anchor: float | None = None) -> None:
        """Change pixels per day by ``factor``, keeping the time under ``anchor`` still."""

        if self.scale is None:
            return
        if anchor is None:
            anchor = self._visible_width() / 2
        when = self.scale.when(self.canvas.canvasx(anchor))
        self._draw(self.scale.pixels_per_day * factor)
        self.canvas.xview_moveto(max(0.0, (self.scale.x(when) - anchor) / self.scale.width))

    def set_placeholder(self, text: str) -> None:
        self._placeholder = text
        if self.scale is None:
            self._draw_placeholder()

    def retranslate(self) -> None:
        self.fit_button.configure(text=self._translate("fit"))
        if self.scale is not None:
            self.scale_label.configure(
                text=describe_zoom(self.scale.pixels_per_day, self._translate)
            )

    def fit(self) -> None:
        if self.range is None:
            return
        self._draw(fit_pixels_per_day(*self.range, self._visible_width()))
        self.canvas.xview_moveto(0)

    def select(self, index: int | None, scroll: bool = True) -> None:
        """Highlight one cluster and, if asked, scroll it into view."""

        self.selected = index
        self._paint_selection()
        bar = self.bar_for(index)
        if scroll and bar is not None and self.scale is not None:
            left = bar.x0 - self._visible_width() / 3
            self.canvas.xview_moveto(max(0.0, left / self.scale.width))

    def bar_for(self, index: int | None) -> Bar | None:
        return next((bar for bar in self.bars if bar.index == index), None)

    def _visible_width(self) -> float:
        width = self.canvas.winfo_width()
        return width if width > 1 else 900

    def _bar_index(self) -> int | None:
        tags = self.canvas.gettags("current")
        index = next(
            (int(tag[1:]) for tag in tags if len(tag) > 1 and tag[0] == "c" and tag[1:].isdigit()),
            None,
        )
        if index is not None and "bar" in tags:
            return index
        return None

    def _clicked(self, event: tk.Event) -> None:
        if self.scale is None:
            return
        index = self._bar_index()
        if index is not None:
            if self._on_select:
                self._on_select(index)
        elif self._on_time:
            self._on_time(self.scale.when(self.canvas.canvasx(event.x)))

    def _double(self, event: tk.Event) -> None:
        """Open the folder for the orange selection."""

        if self.scale is None or self._on_open is None:
            return
        index = self._bar_index()
        if index is None or index != self.selected:
            return
        self._on_open(index)

    def _scroll(self, steps: int) -> str:
        self.canvas.xview_scroll(steps * 3, "units")
        return "break"

    def _wheel(self, event: tk.Event) -> str:
        return self._scroll(-1 if event.delta > 0 else 1)

    def _zoom_wheel(self, event: tk.Event) -> str:
        self.zoom(ZOOM_STEP if event.delta > 0 else 1 / ZOOM_STEP, anchor=event.x)
        return "break"


trace_module(sys.modules[__name__])
