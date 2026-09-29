"""Paint the timeline canvas: the axis, the bars, the file ticks, and the orange selection.

Author: Rajas Chavadekar (rvchavadekar@gmail.com). Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import sys

from filenamecluster.log import trace_module
from . import theme
from .i18n import t
from .layout import TimeScale, axis_ticks, file_marks, layout_bars

AXIS_Y = 26
LANE_TOP = 38
LANE_HEIGHT = 26
BAR_HEIGHT = 18
MARK_HEIGHT = 14


def describe_zoom(pixels_per_day: float, translate=t) -> str:
    if pixels_per_day >= 24:
        return translate("zoom_hour", n=f"{pixels_per_day / 24:.0f}")
    if pixels_per_day >= 1:
        return translate("zoom_day", n=f"{pixels_per_day:.0f}")
    return translate("zoom_month", n=f"{pixels_per_day * 30:.0f}")


class TimelinePainter:
    """Draw ``clusters`` on ``canvas`` at one pixels-per-day scale."""

    def _draw_placeholder(self) -> None:
        self.canvas.delete("all")
        self.scale_label.configure(text="")
        self.canvas.configure(scrollregion=(0, 0, 1, 1))
        self.canvas.create_text(
            theme.px(16),
            theme.px(24),
            anchor="w",
            text=self._placeholder,
            fill=theme.MUTED,
            font=self._small,
        )

    def _draw(self, pixels_per_day: float) -> None:
        assert self.range is not None
        scale = TimeScale(*self.range, pixels_per_day)
        self.scale = scale
        self.bars = layout_bars(self.clusters, scale)
        canvas = self.canvas
        canvas.delete("all")

        axis_y = theme.px(AXIS_Y)
        lane_top = theme.px(LANE_TOP)
        lane_height = theme.px(LANE_HEIGHT)
        bar_height = theme.px(BAR_HEIGHT)
        mark_height = theme.px(MARK_HEIGHT)
        lanes = max((bar.lane for bar in self.bars), default=0) + 1
        marks_top = lane_top + lanes * lane_height + theme.px(4)
        height = marks_top + mark_height + theme.px(8)
        width = scale.width

        ticks = axis_ticks(scale)
        for tick in ticks:
            if not tick.major:
                canvas.create_line(tick.x, axis_y, tick.x, height, fill=theme.GRID_MINOR)
        for tick in ticks:
            if tick.major:
                canvas.create_line(tick.x, axis_y - theme.px(6), tick.x, height, fill=theme.GRID_MAJOR)
                canvas.create_text(
                    tick.x + theme.px(3),
                    axis_y - theme.px(4),
                    anchor="sw",
                    text=tick.label,
                    fill=theme.MUTED,
                    font=self._small,
                )
        canvas.create_line(0, axis_y, width, axis_y, fill=theme.BORDER)

        for bar in self.bars:
            cluster = self.clusters[bar.index]
            top = lane_top + bar.lane * lane_height
            tags = ("bar", f"c{bar.index}")
            canvas.create_rectangle(
                bar.x0,
                top,
                bar.x1,
                top + bar_height,
                fill=theme.BAR_FILLS[cluster.number % 2],
                outline=theme.BAR_OUTLINE,
                tags=(*tags, "rect"),
            )
            canvas.create_text(
                bar.x0 + theme.px(3),
                top + bar_height / 2,
                anchor="w",
                text=str(cluster.number),
                fill=theme.TEXT,
                font=self._small,
                tags=tags,
            )

        for x in file_marks(self.clusters, scale):
            canvas.create_line(x, marks_top, x, marks_top + mark_height, fill=theme.FILE_MARK)

        canvas.configure(scrollregion=(0, 0, width, height))
        self.scale_label.configure(
            text=describe_zoom(scale.pixels_per_day, self._translate)
        )
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


trace_module(sys.modules[__name__])
