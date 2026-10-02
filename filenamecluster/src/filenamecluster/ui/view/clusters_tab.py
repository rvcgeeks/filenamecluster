"""The Clusters tab: timeline, calendar, cluster list, and Day detail.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import sys
from datetime import date, datetime, time, timedelta
from tkinter import ttk

from filenamecluster.log import trace_module
from .calendar import CalendarView
from .folder_name import FolderNameEditor
from .timeline import TimelineView


class ClustersTab:
    """Draw the clusters and report which row, bar, or day the user picked."""

    def __init__(self, host, kit) -> None:
        self.host = host
        self.kit = kit
        self._suppress_select = False

    def build(self) -> None:
        tab = ttk.Frame(self.host.notebook, padding=10)
        self.kit.add_tab(tab, "tab_clusters")
        overview = self.kit.text(ttk.LabelFrame(tab, padding=8), "timeline_frame")
        overview.pack(fill="x")
        self.overview = TimelineView(
            overview,
            height=130,
            min_pixels_per_day=2.0,
            placeholder=self.host.translate("placeholder_timeline"),
            on_select=self.host.actions.select_cluster,
            on_time=lambda when: self.host.actions.day_chosen(when.date()),
            on_open=self.host.actions.open_cluster_folder,
            translate=self.host.translate,
            fonts=self.host.fonts,
        )
        self.overview.pack(fill="x")

        panes = ttk.Panedwindow(tab, orient="horizontal")
        panes.pack(fill="both", expand=True, pady=(10, 0))

        calendar_frame = self.kit.text(ttk.LabelFrame(panes, padding=8), "calendar")
        self.calendar = CalendarView(
            calendar_frame,
            on_day=self.host.actions.day_chosen,
            on_open=self.host.actions.open_cluster_folder,
            translate=self.host.translate,
            fonts=self.host.fonts,
        )
        self.calendar.pack(fill="both", expand=True)
        panes.add(calendar_frame, weight=3)

        list_frame = self.kit.text(ttk.LabelFrame(panes, padding=8), "clusters")
        self.cluster_tree = self.kit.tree(
            list_frame,
            (
                ("number", "col_number", 64, "e"),
                ("name", "col_folder", 320, "w"),
                ("files", "col_files", 110, "e"),
            ),
        )
        for column in ("number", "files"):
            self.cluster_tree.heading(
                column, command=lambda col=column: self.host.actions.sort_clusters(col)
            )
        self.cluster_tree.bind("<<TreeviewSelect>>", self.on_selected)
        self.cluster_tree.bind("<Double-1>", self.on_opened)
        self.folder_names = FolderNameEditor(self.host, self.cluster_tree)
        self.folder_names.bind()
        panes.add(list_frame, weight=3)

        self.day_frame = self.kit.text(ttk.LabelFrame(panes, padding=8), "day_detail")
        self.day_view = TimelineView(
            self.day_frame,
            height=90,
            placeholder=self.host.translate("placeholder_day"),
            on_select=lambda index: self.host.actions.select_cluster(index, show_day=False),
            on_open=self.host.actions.open_cluster_folder,
            translate=self.host.translate,
            fonts=self.host.fonts,
        )
        self.day_view.pack(fill="x")
        self.day_tree = self.kit.tree(
            self.day_frame,
            (
                ("time", "col_time", 80, "w"),
                ("name", "col_file", 280, "w"),
                ("event", "col_event", 60, "e"),
            ),
        )
        self.day_tree.bind("<Double-1>", self.on_day_file)
        panes.add(self.day_frame, weight=4)

    def flush_rename(self) -> None:
        self.folder_names.close(save=True)

    def show_clusters(self, clusters, days, order, sort, selected) -> None:
        self.folder_names.close(save=False)
        self._suppress_select = True
        try:
            self.overview.show(clusters)
            self.calendar.set_clusters(clusters, days)
            self.cluster_tree.delete(*self.cluster_tree.get_children())
            for index in order:
                cluster = clusters[index]
                self.cluster_tree.insert(
                    "",
                    "end",
                    iid=str(index),
                    values=(cluster.number, cluster.name, len(cluster.files)),
                )
            self.show_cluster_sort(order, selected, sort)
        finally:
            self._suppress_select = False

    def highlight_cluster(self, index: int) -> None:
        self._suppress_select = True
        try:
            self.overview.select(index)
            self.day_view.select(index, scroll=False)
            self.calendar.select_cluster(index)
            if self.cluster_tree.selection() != (str(index),):
                self.cluster_tree.selection_set(str(index))
            self.cluster_tree.see(str(index))
        finally:
            self._suppress_select = False

    def present_day(self, day: date, clusters, entries, selected: int | None) -> None:
        self.calendar.select_day(day)
        start = datetime.combine(day, time())
        self.day_view.show(clusters, start, start + timedelta(days=1))
        if selected is not None:
            self.day_view.select(selected, scroll=False)
        self.day_tree.delete(*self.day_tree.get_children())
        for row, (when, name, number) in enumerate(entries):
            self.day_tree.insert(
                "", "end", iid=str(row), values=(f"{when:%H:%M:%S}", name, number)
            )
        count = self.host.translate(
            "file_one" if len(entries) == 1 else "file_many",
            n=len(entries),
        )
        self.day_frame.configure(text=self.day_title(day, count))

    def clear_day(self) -> None:
        self.day_view.show(())
        self.day_tree.delete(*self.day_tree.get_children())
        self.day_frame.configure(text=self.host.translate("day_detail"))

    def show_cluster_sort(self, order, selected, sort) -> None:
        """Draw the order the caller already chose."""

        for position, index in enumerate(order):
            iid = str(index)
            if self.cluster_tree.exists(iid):
                self.cluster_tree.move(iid, "", position)
        if selected is not None and self.cluster_tree.exists(str(selected)):
            self.cluster_tree.see(str(selected))
        self._refresh_headings(sort)

    def selected_row(self) -> int | None:
        selection = self.cluster_tree.selection()
        if not selection:
            return None
        try:
            return int(selection[0])
        except ValueError:
            return None

    def row_at(self, y: int) -> int | None:
        row = self.cluster_tree.identify_row(y)
        if not row or not str(row).isdigit():
            return None
        return int(row)

    def day_row_at(self, y: int) -> int | None:
        row = self.day_tree.identify_row(y)
        if not row or not str(row).isdigit():
            return None
        return int(row)

    def on_selected(self, _event: object | None = None) -> None:
        if self._suppress_select:
            return
        index = self.selected_row()
        if index is not None:
            self.host.actions.cluster_selected(index)

    def on_opened(self, event) -> None:
        index = self.row_at(event.y)
        if index is not None:
            self.host.actions.cluster_opened(index)

    def on_day_file(self, event) -> None:
        row = self.day_row_at(event.y)
        if row is not None:
            self.host.actions.day_file_opened(row)

    def day_title(self, day: date, count: str) -> str:
        when = self.host.translate(
            "date_long",
            weekday=self.host.translate(f"wd_{day.weekday()}"),
            day=day.day,
            month=self.host.translate(f"month_{day.month}"),
            year=day.year,
        )
        return self.host.translate("day_heading", when=when, count=count)

    def _refresh_headings(self, sort) -> None:
        columns = next(cols for tree, cols in self.host.headings if tree is self.cluster_tree)
        for column, key in columns:
            self.cluster_tree.heading(column, text=self.heading_text(column, key, sort))

    def heading_text(self, column: str, key: str, sort) -> str:
        label = self.host.translate(key)
        if sort is not None and sort[0] == column:
            label += " ↓" if sort[1] else " ↑"
        return label


trace_module(sys.modules[__name__])
