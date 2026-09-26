"""Scrollable, zoomable, to-scale timeline drawn on a Tk canvas.

Author: Rajas Chavadekar (rvchavadekar@gmail.com). Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import tkinter as tk
from datetime import datetime
from tkinter import ttk
from typing import Callable, Sequence

from filetimecluster.core.organize import NamedCluster
from filetimecluster.ui import theme
from filetimecluster.ui.i18n import t
from filetimecluster.ui.layout import (
    Bar,
    TimeScale,
    axis_ticks,
    file_marks,
    fit_pixels_per_day,
    layout_bars,
)

AXIS_Y = 26
LANE_TOP = 38
LANE_HEIGHT = 26
BAR_HEIGHT = 18
MARK_HEIGHT = 14
ZOOM_STEP = 1.5


class TimelineView(ttk.Frame):
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
        fonts: dict | None = None,
    ) -> None:
        super().__init__(master)
        self.clusters: tuple[NamedCluster, ...] = ()
        self.range: tuple[datetime, datetime] | None = None
        self.scale: TimeScale | None = None
        self.bars: list[Bar] = []
        self.selected: int | None = None
        self._min_ppd = min_pixels_per_day
        self._placeholder = placeholder
        self._on_select = on_select
        self._on_time = on_time
        self._small = (fonts or {}).get("small")

        tools = ttk.Frame(self)
        tools.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        ttk.Button(tools, text="−", width=3, command=self.zoom_out).pack(side="left")
        ttk.Button(tools, text="+", width=3, command=self.zoom_in).pack(side="left", padx=4)
        self.fit_button = ttk.Button(tools, text=t("fit"), command=self.fit)
        self.fit_button.pack(side="left")
        self.scale_label = ttk.Label(tools, style="Muted.TLabel")
        self.scale_label.pack(side="right")

        self.canvas = tk.Canvas(
            self,
            height=height,
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
        clusters: Sequence[NamedCluster],
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
        self.fit_button.configure(text=t("fit"))
        if self.scale is not None:
            self.scale_label.configure(text=_describe_zoom(self.scale.pixels_per_day))

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

    def _draw_placeholder(self) -> None:
        self.canvas.delete("all")
        self.scale_label.configure(text="")
        self.canvas.configure(scrollregion=(0, 0, 1, 1))
        self.canvas.create_text(
            16, 24, anchor="w", text=self._placeholder, fill=theme.MUTED, font=self._small
        )

    def _draw(self, pixels_per_day: float) -> None:
        assert self.range is not None
        scale = TimeScale(*self.range, pixels_per_day)
        self.scale = scale
        self.bars = layout_bars(self.clusters, scale)
        canvas = self.canvas
        canvas.delete("all")

        lanes = max((bar.lane for bar in self.bars), default=0) + 1
        marks_top = LANE_TOP + lanes * LANE_HEIGHT + 4
        height = marks_top + MARK_HEIGHT + 8
        width = scale.width

        ticks = axis_ticks(scale)
        for tick in ticks:
            if not tick.major:
                canvas.create_line(tick.x, AXIS_Y, tick.x, height, fill=theme.GRID_MINOR)
        for tick in ticks:
            if tick.major:
                canvas.create_line(tick.x, AXIS_Y - 6, tick.x, height, fill=theme.GRID_MAJOR)
                canvas.create_text(
                    tick.x + 3,
                    AXIS_Y - 4,
                    anchor="sw",
                    text=tick.label,
                    fill=theme.MUTED,
                    font=self._small,
                )
        canvas.create_line(0, AXIS_Y, width, AXIS_Y, fill=theme.BORDER)

        for bar in self.bars:
            cluster = self.clusters[bar.index]
            top = LANE_TOP + bar.lane * LANE_HEIGHT
            tags = ("bar", f"c{bar.index}")
            canvas.create_rectangle(
                bar.x0,
                top,
                bar.x1,
                top + BAR_HEIGHT,
                fill=theme.BAR_FILLS[cluster.number % 2],
                outline=theme.BAR_OUTLINE,
                tags=(*tags, "rect"),
            )
            canvas.create_text(
                bar.x0 + 3,
                top + BAR_HEIGHT / 2,
                anchor="w",
                text=str(cluster.number),
                fill=theme.TEXT,
                font=self._small,
                tags=tags,
            )

        for x in file_marks(self.clusters, scale):
            canvas.create_line(x, marks_top, x, marks_top + MARK_HEIGHT, fill=theme.FILE_MARK)

        canvas.configure(scrollregion=(0, 0, width, height))
        self.scale_label.configure(text=_describe_zoom(scale.pixels_per_day))
        self._paint_selection()

    def _paint_selection(self) -> None:
        for bar in self.bars:
            number = self.clusters[bar.index].number
            chosen = bar.index == self.selected
            self.canvas.itemconfigure(
                f"c{bar.index}&&rect",
                fill=theme.SELECTED_FILL if chosen else theme.BAR_FILLS[number % 2],
                outline=theme.SELECTED_OUTLINE if chosen else theme.BAR_OUTLINE,
                width=2 if chosen else 1,
            )

    def _clicked(self, event: tk.Event) -> None:
        if self.scale is None:
            return
        tags = self.canvas.gettags("current")
        index = next(
            (int(tag[1:]) for tag in tags if len(tag) > 1 and tag[0] == "c" and tag[1:].isdigit()),
            None,
        )
        if index is not None and "bar" in tags:
            if self._on_select:
                self._on_select(index)
        elif self._on_time:
            self._on_time(self.scale.when(self.canvas.canvasx(event.x)))

    def _scroll(self, steps: int) -> str:
        self.canvas.xview_scroll(steps * 3, "units")
        return "break"

    def _wheel(self, event: tk.Event) -> str:
        return self._scroll(-1 if event.delta > 0 else 1)

    def _zoom_wheel(self, event: tk.Event) -> str:
        self.zoom(ZOOM_STEP if event.delta > 0 else 1 / ZOOM_STEP, anchor=event.x)
        return "break"


def _describe_zoom(pixels_per_day: float) -> str:
    if pixels_per_day >= 24:
        return t("zoom_hour", n=f"{pixels_per_day / 24:.0f}")
    if pixels_per_day >= 1:
        return t("zoom_day", n=f"{pixels_per_day:.0f}")
    return t("zoom_month", n=f"{pixels_per_day * 30:.0f}")
