"""The window: tabs, tables, and the text on them.

The controller decides what a click does. This module only builds and updates
the widgets.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import json
import sys
import tkinter as tk
from datetime import date
from pathlib import Path

from tkinter import ttk

from filenamecluster.core.parse import LIMIT_FIELDS, PatternRule, TimestampPatterns
from filenamecluster.log import trace_module
from filenamecluster.ui.view import theme
from filenamecluster.ui.view.about import sections
from filenamecluster.ui.view.calendar import CalendarView
from filenamecluster.ui.model.i18n import LANGUAGES, file_count, language, t
from filenamecluster.ui.model.session import DEFAULTS, OPTIONS, AppModel, hours
from filenamecluster.ui.view.timeline import TimelineView


def _cluster_sort_key(raw: str, iid: str) -> tuple[int, int]:
    """Numeric column value, then the cluster index, so equal counts stay stable."""

    try:
        value = int(raw)
    except ValueError:
        value = 0
    return (value, int(iid))


def _icon_path() -> Path:
    """PNG raster of ``ui/assets/icon.svg``, which Tk can load as the window icon."""

    return Path(__file__).resolve().parents[1] / "assets" / "icon.png"


class AppView:
    """Widgets for one ``tk.Tk``. ``controller`` is attached before ``build``."""

    def __init__(self, root: tk.Tk, model: AppModel) -> None:
        self.root = root
        self.model = model
        self.controller = None
        self.fonts = theme.apply(root)
        self._bound: list[ttk.Widget] = []
        self._tab_keys: list[str] = []
        self._headings: list[tuple[ttk.Treeview, tuple[tuple[str, str], ...]]] = []
        self._pattern_editor: ttk.Entry | None = None
        self._input_states: list[tuple[tk.Widget, str]] = []
        self.inputs_locked = False
        self._options_user_sized = False
        self._placing_columns = False
        self._equal_columns_job: str | None = None
        pattern_defaults = TimestampPatterns()
        self.option_vars: dict[str, tk.Variable] = {
            "floor": tk.DoubleVar(root, hours(DEFAULTS.floor)),
            "ceiling": tk.DoubleVar(root, hours(DEFAULTS.ceiling)),
        }
        self.limit_vars = {
            key: tk.IntVar(root, getattr(pattern_defaults, key)) for key, *_rest in LIMIT_FIELDS
        }
        self.folder_text = tk.StringVar(root, t("no_folder"))
        self.status_text = tk.StringVar(root, t("choose_status"))
        self.language_var = tk.StringVar(
            root, next(name for code, name in LANGUAGES if code == language())
        )
        self.logging_var = tk.BooleanVar(root, False)

    def build(self) -> None:
        """Create the header, the status line, and the four tabs."""

        if self.controller is None:
            raise RuntimeError("controller is not attached")
        root = self.root
        root.title(t("app_title"))
        root.geometry("1360x880")
        root.minsize(1040, 680)
        self._install_icon()
        self._build_header()
        self.status = ttk.Label(root, textvariable=self.status_text, style="Status.TLabel")
        self.status.pack(fill="x", side="bottom", pady=(8, 0))
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=(8, 0))
        self._build_clusters_tab()
        self._build_options_tab()
        self._build_skipped_tab()
        self._build_about_tab()

    def _build_header(self) -> None:
        header = ttk.Frame(self.root, style="Header.TFrame", padding=(16, 12))
        header.pack(fill="x")
        text = ttk.Frame(header, style="Header.TFrame")
        text.pack(side="left", fill="x", expand=True)
        self._text(ttk.Label(text, style="Title.TLabel"), "app_title").pack(anchor="w")
        ttk.Label(text, textvariable=self.folder_text, style="Path.TLabel").pack(anchor="w")

        self.apply_button = self._text(
            ttk.Button(
                header,
                style="Accent.TButton",
                command=self.controller.apply_clustering,
                state="disabled",
            ),
            "apply",
        )
        self.apply_button.pack(side="right")
        self.flatten_button = self._text(
            ttk.Button(header, command=self.controller.flatten_clustering, state="disabled"),
            "flatten",
        )
        self.flatten_button.pack(side="right", padx=(0, 8))
        self._text(ttk.Button(header, command=self.controller.choose_folder), "choose_folder").pack(
            side="right", padx=8
        )
        language_box = ttk.Combobox(
            header,
            textvariable=self.language_var,
            values=[name for _code, name in LANGUAGES],
            state="readonly",
            width=12,
        )
        language_box.pack(side="right")
        language_box.bind("<<ComboboxSelected>>", self.controller._language_changed)
        self._text(ttk.Label(header, style="Header.TLabel"), "language").pack(side="right", padx=(0, 6))

    def _build_clusters_tab(self) -> None:
        tab = ttk.Frame(self.notebook, padding=10)
        self._add_tab(tab, "tab_clusters")

        overview = self._text(ttk.LabelFrame(tab, padding=8), "timeline_frame")
        overview.pack(fill="x")
        self.overview = TimelineView(
            overview,
            height=130,
            min_pixels_per_day=2.0,
            placeholder=t("placeholder_timeline"),
            on_select=self.controller.select_cluster,
            on_time=self.controller._timeline_clicked,
            on_open=self.controller.open_cluster_folder,
            fonts=self.fonts,
        )
        self.overview.pack(fill="x")

        panes = ttk.Panedwindow(tab, orient="horizontal")
        panes.pack(fill="both", expand=True, pady=(10, 0))

        calendar_frame = self._text(ttk.LabelFrame(panes, padding=8), "calendar")
        self.calendar = CalendarView(
            calendar_frame,
            on_day=self.controller._day_clicked,
            on_open=self.controller.open_cluster_folder,
            fonts=self.fonts,
        )
        self.calendar.pack(fill="both", expand=True)
        panes.add(calendar_frame, weight=3)

        list_frame = self._text(ttk.LabelFrame(panes, padding=8), "clusters")
        self.cluster_tree = self._tree(
            list_frame,
            (
                ("number", "col_number", 64, "e"),
                ("name", "col_folder", 320, "w"),
                ("files", "col_files", 110, "e"),
            ),
        )
        for column in ("number", "files"):
            self.cluster_tree.heading(
                column, command=lambda col=column: self.controller.sort_clusters(col)
            )
        self.cluster_tree.bind("<<TreeviewSelect>>", self.controller._tree_selected)
        self.cluster_tree.bind("<Double-1>", self.controller._tree_double)
        panes.add(list_frame, weight=3)

        self.day_frame = self._text(ttk.LabelFrame(panes, padding=8), "day_detail")
        self.day_view = TimelineView(
            self.day_frame,
            height=90,
            placeholder=t("placeholder_day"),
            on_select=lambda index: self.controller.select_cluster(index, show_day=False),
            on_open=self.controller.open_cluster_folder,
            fonts=self.fonts,
        )
        self.day_view.pack(fill="x")
        self.day_tree = self._tree(
            self.day_frame,
            (
                ("time", "col_time", 80, "w"),
                ("name", "col_file", 280, "w"),
                ("event", "col_event", 60, "e"),
            ),
        )
        self.day_tree.bind("<Double-1>", self.controller._day_file_double)
        panes.add(self.day_frame, weight=4)

    def _build_options_tab(self) -> None:
        tab = ttk.Frame(self.notebook, padding=(10, 10, 10, 6))
        self._add_tab(tab, "tab_options")
        self._options_user_sized = False
        self._placing_columns = False
        self._equal_columns_job = None

        buttons = ttk.Frame(tab)
        buttons.pack(side="bottom", fill="x", pady=(8, 0))
        self._text(
            ttk.Button(buttons, style="Accent.TButton", command=self.controller.refresh),
            "update_preview",
        ).pack(side="left")
        self._text(
            ttk.Button(buttons, command=self.controller.restore_defaults), "restore_defaults"
        ).pack(side="left", padx=8)
        self.logging_switch = self._text(
            ttk.Checkbutton(
                buttons,
                variable=self.logging_var,
                command=self.controller._logging_toggled,
            ),
            "write_log",
        )
        self.logging_switch.pack(side="right")

        rows = self._split(tab, "vertical")
        rows.pack(fill="both", expand=True)
        self.options_rows = rows

        patterns = self._text(ttk.LabelFrame(rows, padding=8), "patterns_frame")
        self._flowing_help(patterns, "patterns_help")
        self.pattern_tree = self._tree(
            patterns,
            (
                ("description", "col_description", 180, "w"),
                ("pattern", "col_pattern", 520, "w"),
            ),
        )
        self.pattern_tree.configure(height=6)
        self.pattern_tree.bind("<Double-1>", self._edit_pattern_cell)
        self._fill_pattern_table(TimestampPatterns().rules)
        pattern_buttons = ttk.Frame(patterns)
        pattern_buttons.pack(anchor="w", pady=(6, 0))
        self._text(
            ttk.Button(pattern_buttons, command=self.controller.add_pattern_rule), "add_pattern"
        ).pack(side="left")
        self._text(
            ttk.Button(pattern_buttons, command=self.controller.remove_pattern_rule),
            "remove_pattern",
        ).pack(side="left", padx=8)
        rows.add(patterns, stretch="always", minsize=160)

        columns = self._split(rows, "horizontal")
        self.options_columns = columns
        rows.add(columns, stretch="always", minsize=160)

        gaps = self._text(ttk.LabelFrame(columns, padding=8), "safety_limits")
        self.option_inputs: dict[str, ttk.Spinbox] = {}
        for row, (key, label_key, hint_key, (low, high, step)) in enumerate(OPTIONS):
            self.option_inputs[key] = self._option_row(
                gaps, row, label_key, hint_key, self.option_vars[key], low, high, step
            )
        self._reflow(gaps)
        columns.add(gaps, stretch="always", minsize=160, width=240, sticky="nsew")

        limits = self._text(ttk.LabelFrame(columns, padding=8), "years_frame")
        self.limit_inputs: dict[str, ttk.Spinbox] = {}
        for row, (key, _label, _hint, low, high) in enumerate(LIMIT_FIELDS):
            self.limit_inputs[key] = self._option_row(
                limits, row, f"limit_{key}", f"limit_{key}_hint", self.limit_vars[key], low, high, 1
            )
        self._reflow(limits)
        columns.add(limits, stretch="always", minsize=160, width=240, sticky="nsew")

        model = self._text(ttk.LabelFrame(columns, padding=8), "model_frame")
        self._flowing_help(model, "model_help")
        self.model_tree = self._tree(
            model,
            (
                ("parameter", "col_parameter", 140, "w"),
                ("value", "col_value", 110, "w"),
                ("meaning", "col_meaning", 160, "w"),
            ),
        )
        self.model_tree.configure(height=4)
        self._fill_model_view()
        columns.add(model, stretch="always", minsize=160, width=240, sticky="nsew")

        columns.bind("<Configure>", self._balance_options_grid)
        columns.bind("<ButtonPress-1>", self._mark_columns_user_sized, add="+")

    def _split(self, master: tk.Misc, orient: str) -> tk.PanedWindow:
        """A sash the user can drag. Every pane grows when the window grows."""

        return tk.PanedWindow(
            master,
            orient=orient,
            sashwidth=6,
            sashrelief="flat",
            opaqueresize=True,
            background=theme.BORDER,
            bd=0,
            handlesize=0,
        )

    def _option_row(
        self,
        frame: ttk.LabelFrame,
        row: int,
        label_key: str,
        hint_key: str,
        variable: tk.Variable,
        low: float,
        high: float,
        step: float,
    ) -> ttk.Spinbox:
        line = row * 2
        self._text(
            ttk.Label(frame, style="Info.TLabel", wraplength=200, justify="left"),
            label_key,
        ).grid(row=line, column=0, sticky="ew", pady=(4, 0))
        spin = ttk.Spinbox(frame, from_=low, to=high, increment=step, width=8, textvariable=variable)
        spin.grid(row=line, column=1, sticky="e", padx=(8, 0))
        spin.bind("<Return>", lambda event: self.controller.refresh())
        self._text(
            ttk.Label(frame, style="Muted.TLabel", wraplength=160, justify="left"),
            hint_key,
        ).grid(row=line + 1, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        frame.columnconfigure(0, weight=1)
        return spin

    def _reflow(self, frame: ttk.LabelFrame) -> None:
        """Wrap hint text to the pane width as the sash moves."""

        def fit(event: tk.Event, frame: ttk.LabelFrame = frame) -> None:
            width = event.width - 28
            if width < 80:
                return
            for child in frame.winfo_children():
                style = str(child.cget("style"))
                if style == "Muted.TLabel":
                    target = width
                elif style == "Info.TLabel":
                    target = max(width - 96, 80)
                else:
                    continue
                if abs(int(child.cget("wraplength")) - target) < 4:
                    continue
                child.configure(wraplength=target)

        frame.bind("<Configure>", fit)

    def _flowing_help(self, frame: ttk.LabelFrame, key: str) -> None:
        label = self._text(
            ttk.Label(frame, style="Muted.TLabel", wraplength=280, justify="left"),
            key,
        )
        label.pack(anchor="w", fill="x", pady=(0, 6))

        def fit(event: tk.Event, label: ttk.Label = label) -> None:
            width = event.width - 20
            if width >= 80 and abs(int(label.cget("wraplength")) - width) >= 4:
                label.configure(wraplength=width)

        frame.bind("<Configure>", fit, add="+")

    def _mark_columns_user_sized(self, event: tk.Event) -> None:
        """A sash drag should stick. Later window resizes must not snap it back."""

        if self._placing_columns or self.options_columns.winfo_width() < 200:
            return
        for index in range(2):
            sash_x, _sash_y = self.options_columns.sash_coord(index)
            if abs(event.x - sash_x) <= 8:
                self._options_user_sized = True
                return

    def _balance_options_grid(self, event: tk.Event) -> None:
        """Keep scheduling an even split until the row has its real width."""

        if self._options_user_sized or self._placing_columns or event.width < 200:
            return
        if self._equal_columns_job is not None:
            return
        self._equal_columns_job = self.root.after_idle(self._finish_equal_columns)

    def _finish_equal_columns(self) -> None:
        self._equal_columns_job = None
        if self._options_user_sized:
            return
        width = self.options_columns.winfo_width()
        if width < 200:
            return
        self._place_equal_columns(width)

    def _place_equal_columns(self, width: int) -> None:
        actual = self.options_columns.winfo_width()
        if actual >= 200:
            width = actual
        sash = int(self.options_columns.cget("sashwidth"))
        pane = max((width - 2 * sash) // 3, 1)
        target = pane * 2 + sash
        try:
            current = self.options_columns.sash_coord(0)[0]
            following = self.options_columns.sash_coord(1)[0]
        except tk.TclError:
            current = following = -1
        if abs(current - pane) < 3 and abs(following - target) < 3:
            return
        self._placing_columns = True
        try:
            for child in self.options_columns.panes():
                self.options_columns.paneconfigure(child, width=pane)
            self.options_columns.sash_place(0, pane, 1)
            self.options_columns.sash_place(1, target, 1)
        finally:
            self._placing_columns = False

    def _build_skipped_tab(self) -> None:
        tab = ttk.Frame(self.notebook, padding=10)
        self._add_tab(tab, "tab_skipped")
        self._text(ttk.Label(tab, style="Muted.TLabel"), "skipped_intro").pack(anchor="w", pady=(0, 6))
        self.skipped_tree = self._tree(
            tab, (("name", "col_name", 480, "w"), ("reason", "col_reason", 260, "w"))
        )

    def _build_about_tab(self) -> None:
        tab = ttk.Frame(self.notebook, padding=10)
        self._add_tab(tab, "tab_about")
        text = tk.Text(
            tab,
            wrap="word",
            background=theme.SURFACE,
            foreground=theme.TEXT,
            relief="flat",
            padx=24,
            pady=18,
            highlightthickness=1,
            highlightbackground=theme.BORDER,
            font=self.fonts["small"],
            spacing3=4,
        )
        bar = ttk.Scrollbar(tab, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=bar.set)
        bar.pack(side="right", fill="y")
        text.pack(fill="both", expand=True)
        text.tag_configure(
            "heading",
            font=self.fonts["heading"],
            foreground=theme.ACCENT_ACTIVE,
            spacing1=12,
            spacing3=6,
        )
        self.about_text = text
        self._fill_about()

    def _tree(self, master: tk.Misc, columns: tuple) -> ttk.Treeview:
        frame = ttk.Frame(master)
        frame.pack(fill="both", expand=True, pady=(6, 0))
        tree = ttk.Treeview(
            frame, columns=[key for key, *_ in columns], show="headings", selectmode="browse"
        )
        for key, heading_key, width, anchor in columns:
            tree.heading(key, text=t(heading_key), anchor=anchor)
            tree.column(
                key,
                width=width,
                anchor=anchor,
                stretch=key in {"name", "pattern", "meaning", "parameter", "value"},
            )
        self._headings.append((tree, tuple((key, heading_key) for key, heading_key, *_rest in columns)))
        bar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=bar.set)
        tree.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")
        return tree

    def _text(self, widget, key: str):
        widget._i18n_key = key
        widget.configure(text=t(key))
        self._bound.append(widget)
        return widget

    def _add_tab(self, tab: ttk.Frame, key: str) -> None:
        self.notebook.add(tab, text=t(key))
        self._tab_keys.append(key)

    def _set_status(self, message: str, error: bool = False) -> None:
        self.status_text.set(message)
        self.status.configure(style="Error.TLabel" if error else "Status.TLabel")

    def _fill_about(self) -> None:
        text = self.about_text
        text.configure(state="normal")
        text.delete("1.0", "end")
        for heading, body in sections():
            text.insert("end", heading + "\n", "heading")
            text.insert("end", body + "\n")
        text.configure(state="disabled")

    def _fill_model_view(self) -> None:
        """Show every learned field of the model JSON. The table cannot edit them."""

        self.model_tree.delete(*self.model_tree.get_children())
        learned = self.model.result.model if self.model.result is not None else None
        loaded = self.model.result is not None
        fields = (
            ("within_hours", "model_within"),
            ("between_hours", "model_between"),
            ("boundary_hours", "model_boundary"),
            ("separated", "model_separated"),
        )
        for key, meaning_key in fields:
            if not loaded:
                value = t("model_value_pending")
            elif learned is None:
                value = "null"
            elif key == "separated":
                value = "true" if learned.separated else "false"
            else:
                value = json.dumps(getattr(learned, key))
            self.model_tree.insert(
                "",
                "end",
                iid=key,
                values=(f"learned.{key}", value, t(meaning_key)),
            )

    def _fill_skipped(self, result) -> None:
        from filenamecluster.core.organize import is_cluster_folder_name

        self.skipped_tree.delete(*self.skipped_tree.get_children())
        for name in result.ignored_directories:
            reason = t("reason_event" if is_cluster_folder_name(name) else "reason_subfolder")
            self.skipped_tree.insert("", "end", values=(name, reason))
        for name in result.ignored_without_timestamp:
            self.skipped_tree.insert("", "end", values=(name, t("reason_no_timestamp")))

    def _day_title(self, day: date, count: str) -> str:
        when = t(
            "date_long",
            weekday=t(f"wd_{day.weekday()}"),
            day=day.day,
            month=t(f"month_{day.month}"),
            year=day.year,
        )
        return t("day_heading", when=when, count=count)

    def retranslate(self) -> None:
        """Apply the current catalog to the window without scanning the folder again."""

        self.root.title(t("app_title"))
        for widget in self._bound:
            widget.configure(text=t(widget._i18n_key))
        for iid in self.pattern_tree.get_children():
            if str(iid).startswith("custom-") or iid in self.model.pattern_desc_dirty:
                continue
            self.pattern_tree.set(iid, "description", t(f"pattern_{iid}"))
        for index, key in enumerate(self._tab_keys):
            self.notebook.tab(index, text=t(key))
        for tree, columns in self._headings:
            for column, key in columns:
                text = self._cluster_heading_text(column, key) if tree is self.cluster_tree else t(key)
                tree.heading(column, text=text)
        self._fill_about()
        self._fill_model_view()
        self.overview.set_placeholder(t("placeholder_timeline"))
        self.overview.retranslate()
        self.day_view.set_placeholder(t("placeholder_day"))
        self.day_view.retranslate()
        theme.use_script(self.root, self.fonts, language())
        self.calendar.redraw()
        if self.model.directory is None:
            self.folder_text.set(t("no_folder"))
        if self.model.result is not None:
            self._fill_skipped(self.model.result)
            if self.model.selected_day is not None:
                count = file_count(len(self.model.files_by_day.get(self.model.selected_day, [])))
                self.day_frame.configure(text=self._day_title(self.model.selected_day, count))
            else:
                self.day_frame.configure(text=t("day_detail"))
        message, error = self.model.status_builder()
        self._set_status(message, error)

    def _fill_pattern_table(
        self, rules: tuple[PatternRule, ...], honor_saved_descriptions: bool = False
    ) -> None:
        self._close_pattern_editor(save=False)
        self.pattern_tree.delete(*self.pattern_tree.get_children())
        self.model.pattern_desc_dirty.clear()
        self.model.custom_pattern_seq = 1
        for rule in rules:
            iid = rule.key or f"custom-{self.model.custom_pattern_seq}"
            if str(iid).startswith("custom-"):
                self.model.custom_pattern_seq = max(
                    self.model.custom_pattern_seq, int(str(iid).split("-", 1)[1]) + 1
                )
            if rule.key and honor_saved_descriptions:
                catalog = t(f"pattern_{rule.key}")
                if rule.description != catalog:
                    self.model.pattern_desc_dirty.add(str(iid))
                    description = rule.description
                else:
                    description = catalog
            elif rule.key:
                description = t(f"pattern_{rule.key}")
            else:
                description = rule.description
            self.pattern_tree.insert("", "end", iid=iid, values=(description, rule.pattern))

    def _edit_pattern_cell(self, event: tk.Event) -> None:
        if self.inputs_locked:
            return
        row = self.pattern_tree.identify_row(event.y)
        column = self.pattern_tree.identify_column(event.x)
        if not row or column not in {"#1", "#2"}:
            return
        name = self.pattern_tree["columns"][int(column[1:]) - 1]
        self._begin_pattern_edit(row, name)

    def _begin_pattern_edit(self, iid: str, column: str) -> None:
        if self.inputs_locked:
            return
        self._close_pattern_editor(save=True)
        tree = self.pattern_tree
        bbox = tree.bbox(iid, column)
        if not bbox:
            return
        x, y, width, height = bbox
        entry = ttk.Entry(tree)
        entry.insert(0, tree.set(iid, column))
        entry.select_range(0, "end")
        entry.place(x=x, y=y, width=max(width, 80), height=height)
        entry.focus_set()
        self._pattern_editor = entry

        def commit(_event: tk.Event | None = None) -> None:
            if self._pattern_editor is not entry:
                return
            self._pattern_editor = None
            value = entry.get()
            entry.destroy()
            tree.set(iid, column, value)
            if column == "description" and not str(iid).startswith("custom-"):
                if value != t(f"pattern_{iid}"):
                    self.model.pattern_desc_dirty.add(str(iid))
                else:
                    self.model.pattern_desc_dirty.discard(str(iid))

        def cancel(_event: tk.Event | None = None) -> str:
            if self._pattern_editor is entry:
                self._pattern_editor = None
                entry.destroy()
            return "break"

        entry.bind("<Return>", commit)
        entry.bind("<FocusOut>", commit)
        entry.bind("<Escape>", cancel)

    def lock_inputs(self) -> None:
        """Disable buttons and option controls. Viewing the drawings stays possible."""

        self._close_pattern_editor(save=True)
        self.inputs_locked = True
        locked: list[tuple[tk.Widget, str]] = []
        for widget in self._input_widgets():
            previous = str(widget.cget("state"))
            locked.append((widget, previous))
            widget.configure(state="disabled")
        self._input_states = locked

    def unlock_inputs(self) -> None:
        """Put buttons and option controls back to the states they had before the lock."""

        self.inputs_locked = False
        for widget, previous in self._input_states:
            try:
                widget.configure(state=previous)
            except tk.TclError:
                continue
        self._input_states = []

    def _input_widgets(self) -> list[tk.Widget]:
        found: list[tk.Widget] = []

        def walk(widget: tk.Misc) -> None:
            for child in widget.winfo_children():
                if isinstance(child, (ttk.Button, ttk.Spinbox, ttk.Checkbutton, ttk.Combobox)):
                    found.append(child)
                walk(child)

        walk(self.root)
        return found

    def _close_pattern_editor(self, save: bool) -> None:
        entry = self._pattern_editor
        if entry is None:
            return
        if save:
            entry.event_generate("<Return>")
            return
        self._pattern_editor = None
        entry.destroy()

    def _apply_cluster_sort(self) -> None:
        sort = self.model.cluster_sort
        rows = list(self.cluster_tree.get_children())
        if sort is not None and rows:
            column, descending = sort
            rows.sort(
                key=lambda iid: _cluster_sort_key(self.cluster_tree.set(iid, column), iid),
                reverse=descending,
            )
            for index, iid in enumerate(rows):
                self.cluster_tree.move(iid, "", index)
            if self.model.selected_cluster is not None:
                self.cluster_tree.see(str(self.model.selected_cluster))
        self._refresh_cluster_headings()

    def _refresh_cluster_headings(self) -> None:
        columns = next(cols for tree, cols in self._headings if tree is self.cluster_tree)
        for column, key in columns:
            self.cluster_tree.heading(column, text=self._cluster_heading_text(column, key))

    def _cluster_heading_text(self, column: str, key: str) -> str:
        label = t(key)
        if self.model.cluster_sort is not None and self.model.cluster_sort[0] == column:
            label += " ↓" if self.model.cluster_sort[1] else " ↑"
        return label

    def _install_icon(self) -> None:
        """Use the PNG raster of ``icon.svg``. Tk does not load SVG or ICO here."""

        try:
            self._icon = tk.PhotoImage(file=str(_icon_path()))
        except tk.TclError:
            return
        self.root.iconphoto(True, self._icon)


trace_module(sys.modules[__name__])
