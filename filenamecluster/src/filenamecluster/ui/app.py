"""Main window: choose a folder, preview the events, then apply clustering.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Introduction: ``readme.md``. Mathematics: ``docs/algorithm.md``.
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import tkinter as tk
from datetime import date, datetime, time, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from filenamecluster.core.cluster import ClusterParams
from filenamecluster.core.model_file import MODEL_NAME
from filenamecluster.core.organize import (
    flatten_cluster_folders,
    is_cluster_folder_name,
    move_into_cluster_folders,
)
from filenamecluster.core.parse import (
    LIMIT_FIELDS,
    PATTERN_FIELDS,
    TimestampPatterns,
    TimestampedFile,
)
from filenamecluster.core.pipeline import ClusterResult, cluster_directory
from filenamecluster.ui import theme
from filenamecluster.ui.about import sections
from filenamecluster.ui.calendar_view import CalendarView
from filenamecluster.ui.i18n import LANGUAGES, file_count, language, set_language, t
from filenamecluster.ui.timeline import TimelineView

DEFAULTS = ClusterParams()

OPTIONS = (
    ("floor", "floor_label", "floor_hint", (0.5, 168, 0.5)),
    ("ceiling", "ceiling_label", "ceiling_hint", (1, 8760, 1)),
)

_PATTERN_TEXT = {
    "clock_separated": ("pattern_clock_separated", "groups_clock_ms"),
    "clock_compact_sep": ("pattern_clock_compact_sep", "groups_clock_ms"),
    "clock_compact_17": ("pattern_clock_compact_17", "groups_clock_ms"),
    "clock_compact_14": ("pattern_clock_compact_14", "groups_clock"),
    "numeric_date": ("pattern_numeric_date", "groups_day_month"),
    "epoch_ms": ("pattern_epoch_ms", "groups_epoch"),
    "date_only": ("pattern_date_only", "groups_date"),
}


def _hours(delta: timedelta) -> float:
    return delta.total_seconds() / 3600


class ClusterApp:
    """The whole application, attached to one Tk root."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.fonts = theme.apply(root)
        self._bound: list[ttk.Widget] = []
        self._pattern_hints: list[tuple[ttk.Label, str, str]] = []
        self._tab_keys: list[str] = []
        self._headings: list[tuple[ttk.Treeview, tuple[tuple[str, str], ...]]] = []
        self._status_builder = lambda: (t("choose_status"), False)
        root.title(t("app_title"))
        root.geometry("1360x880")
        root.minsize(1040, 680)
        self._install_icon()

        self.directory: Path | None = None
        self.result: ClusterResult | None = None
        self.selected_cluster: int | None = None
        self.selected_day: date | None = None
        self.files_by_day: dict[date, list[tuple[TimestampedFile, int]]] = {}

        self.option_vars: dict[str, tk.Variable] = {
            "floor": tk.DoubleVar(root, _hours(DEFAULTS.floor)),
            "ceiling": tk.DoubleVar(root, _hours(DEFAULTS.ceiling)),
        }
        pattern_defaults = TimestampPatterns()
        self.limit_vars = {
            key: tk.IntVar(root, getattr(pattern_defaults, key)) for key, *_rest in LIMIT_FIELDS
        }
        self.pattern_vars = {
            key: tk.StringVar(root, getattr(pattern_defaults, key))
            for key, *_rest in PATTERN_FIELDS
        }
        self.folder_text = tk.StringVar(root, t("no_folder"))
        self.status_text = tk.StringVar(root, t("choose_status"))
        self.language_var = tk.StringVar(root, next(name for code, name in LANGUAGES if code == language()))

        self._build_header()
        self.status = ttk.Label(root, textvariable=self.status_text, style="Status.TLabel")
        self.status.pack(fill="x", side="bottom", pady=(8, 0))
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=(8, 0))
        self._build_clusters_tab()
        self._build_options_tab()
        self._build_skipped_tab()
        self._build_about_tab()

    # ---- layout -------------------------------------------------------------

    def _build_header(self) -> None:
        header = ttk.Frame(self.root, style="Header.TFrame", padding=(16, 12))
        header.pack(fill="x")
        text = ttk.Frame(header, style="Header.TFrame")
        text.pack(side="left", fill="x", expand=True)
        self._text(ttk.Label(text, style="Title.TLabel"), "app_title").pack(anchor="w")
        ttk.Label(text, textvariable=self.folder_text, style="Path.TLabel").pack(anchor="w")

        self.apply_button = self._text(
            ttk.Button(header, style="Accent.TButton", command=self.apply_clustering, state="disabled"),
            "apply",
        )
        self.apply_button.pack(side="right")
        self.flatten_button = self._text(
            ttk.Button(header, command=self.flatten_clustering, state="disabled"),
            "flatten",
        )
        self.flatten_button.pack(side="right", padx=(0, 8))
        self._text(ttk.Button(header, command=self.choose_folder), "choose_folder").pack(
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
        language_box.bind("<<ComboboxSelected>>", self._language_changed)
        self._text(ttk.Label(header, style="Header.TLabel"), "language").pack(
            side="right", padx=(0, 6)
        )

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
            on_select=self.select_cluster,
            on_time=self._timeline_clicked,
            fonts=self.fonts,
        )
        self.overview.pack(fill="x")

        panes = ttk.Panedwindow(tab, orient="horizontal")
        panes.pack(fill="both", expand=True, pady=(10, 0))

        calendar_frame = self._text(ttk.LabelFrame(panes, padding=8), "calendar")
        self.calendar = CalendarView(calendar_frame, on_day=self._day_clicked, fonts=self.fonts)
        self.calendar.pack(fill="both", expand=True)
        panes.add(calendar_frame, weight=3)

        list_frame = self._text(ttk.LabelFrame(panes, padding=8), "clusters")
        self.cluster_tree = self._tree(
            list_frame,
            (("number", "col_number", 50, "e"), ("name", "col_folder", 320, "w"), ("files", "col_files", 60, "e")),
        )
        self.cluster_tree.bind("<<TreeviewSelect>>", self._tree_selected)
        panes.add(list_frame, weight=3)

        self.day_frame = self._text(ttk.LabelFrame(panes, padding=8), "day_detail")
        self.day_view = TimelineView(
            self.day_frame,
            height=90,
            placeholder=t("placeholder_day"),
            on_select=lambda index: self.select_cluster(index, show_day=False),
            fonts=self.fonts,
        )
        self.day_view.pack(fill="x")
        self.day_tree = self._tree(
            self.day_frame,
            (("time", "col_time", 80, "w"), ("name", "col_file", 280, "w"), ("event", "col_event", 60, "e")),
        )
        panes.add(self.day_frame, weight=4)

    def _build_options_tab(self) -> None:
        tab = ttk.Frame(self.notebook, padding=(10, 10, 10, 6))
        self._add_tab(tab, "tab_options")
        canvas = tk.Canvas(tab, background=theme.BACKGROUND, highlightthickness=0)
        bar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=bar.set)
        bar.pack(side="right", fill="y")
        canvas.pack(side="top", fill="both", expand=True)
        inner = ttk.Frame(canvas, padding=(6, 4, 12, 8))
        window = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(window, width=event.width))
        canvas.bind("<MouseWheel>", self._scroll_options)
        inner.bind("<MouseWheel>", self._scroll_options)
        self.options_canvas = canvas

        gaps = self._text(ttk.LabelFrame(inner, padding=14), "safety_limits")
        gaps.pack(fill="x")
        self.option_inputs: dict[str, ttk.Spinbox] = {}
        for row, (key, label_key, hint_key, (low, high, step)) in enumerate(OPTIONS):
            self.option_inputs[key] = self._option_row(
                gaps, row, label_key, hint_key, self.option_vars[key], low, high, step
            )

        limits = self._text(ttk.LabelFrame(inner, padding=14), "years_frame")
        limits.pack(fill="x", pady=(12, 0))
        self.limit_inputs: dict[str, ttk.Spinbox] = {}
        for row, (key, _label, _hint, low, high) in enumerate(LIMIT_FIELDS):
            self.limit_inputs[key] = self._option_row(
                limits, row, f"limit_{key}", f"limit_{key}_hint", self.limit_vars[key], low, high, 1
            )

        patterns = self._text(ttk.LabelFrame(inner, padding=14), "patterns_frame")
        patterns.pack(fill="x", pady=(12, 0))
        self._text(
            ttk.Label(patterns, wraplength=860, style="Muted.TLabel"),
            "patterns_help",
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))
        self.pattern_inputs: dict[str, ttk.Entry] = {}
        for row, (key, _label, example, _groups) in enumerate(PATTERN_FIELDS, start=1):
            label_key, groups_key = _PATTERN_TEXT[key]
            self._text(ttk.Label(patterns, style="Info.TLabel"), label_key).grid(
                row=row, column=0, sticky="w", pady=4
            )
            entry = ttk.Entry(patterns, textvariable=self.pattern_vars[key])
            entry.grid(row=row, column=1, sticky="ew", padx=12)
            entry.bind("<Return>", lambda event: self.refresh())
            self.pattern_inputs[key] = entry
            hint = ttk.Label(patterns, style="Muted.TLabel")
            hint.grid(row=row, column=2, sticky="w")
            self._pattern_hints.append((hint, example, groups_key))
            hint.configure(text=f"{example}  ·  {t(groups_key)}")
        patterns.columnconfigure(1, weight=1)

        buttons = ttk.Frame(tab)
        buttons.pack(fill="x", pady=(8, 0))
        self._text(
            ttk.Button(buttons, style="Accent.TButton", command=self.refresh),
            "update_preview",
        ).pack(side="left")
        self._text(ttk.Button(buttons, command=self.restore_defaults), "restore_defaults").pack(
            side="left", padx=8
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
        self._text(ttk.Label(frame, style="Info.TLabel"), label_key).grid(
            row=row, column=0, sticky="w", pady=6
        )
        spin = ttk.Spinbox(
            frame, from_=low, to=high, increment=step, width=8, textvariable=variable
        )
        spin.grid(row=row, column=1, sticky="w", padx=12)
        spin.bind("<Return>", lambda event: self.refresh())
        self._text(ttk.Label(frame, style="Muted.TLabel"), hint_key).grid(row=row, column=2, sticky="w")
        return spin

    def _scroll_options(self, event: tk.Event) -> str:
        self.options_canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")
        return "break"

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
            tree.column(key, width=width, anchor=anchor, stretch=key == "name")
        self._headings.append((tree, tuple((key, heading_key) for key, heading_key, *_rest in columns)))
        bar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=bar.set)
        tree.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")
        return tree

    # ---- actions ------------------------------------------------------------

    def choose_folder(self) -> None:
        start = Path.cwd() / "data"
        chosen = filedialog.askdirectory(
            parent=self.root,
            title=t("choose_title"),
            initialdir=start if start.is_dir() else Path.cwd(),
            mustexist=True,
        )
        if chosen:
            self.load_folder(Path(chosen))

    def load_folder(self, folder: Path) -> bool:
        self.directory = Path(folder)
        self.folder_text.set(str(self.directory))
        return self.refresh()

    def read_params(self) -> ClusterParams:
        values: dict[str, float] = {}
        for key, label_key, *_rest in OPTIONS:
            try:
                values[key] = self.option_vars[key].get()
            except tk.TclError:
                raise ValueError(t("must_be_number", label=t(label_key))) from None
        return ClusterParams(
            floor=timedelta(hours=values["floor"]),
            ceiling=timedelta(hours=values["ceiling"]),
        )

    def read_patterns(self) -> TimestampPatterns:
        limits: dict[str, int] = {}
        for key, _label, _hint, low, high in LIMIT_FIELDS:
            label = t(f"limit_{key}")
            try:
                value = int(self.limit_vars[key].get())
            except (tk.TclError, ValueError):
                raise ValueError(t("must_be_whole", label=label)) from None
            if not low <= value <= high:
                raise ValueError(t("must_be_between", label=label, low=low, high=high))
            limits[key] = value
        texts = {key: self.pattern_vars[key].get() for key, *_rest in PATTERN_FIELDS}
        patterns = TimestampPatterns(**texts, **limits)
        patterns.compile()
        return patterns

    def restore_defaults(self) -> None:
        self.option_vars["floor"].set(_hours(DEFAULTS.floor))
        self.option_vars["ceiling"].set(_hours(DEFAULTS.ceiling))
        patterns = TimestampPatterns()
        for key, *_rest in LIMIT_FIELDS:
            self.limit_vars[key].set(getattr(patterns, key))
        for key, *_rest in PATTERN_FIELDS:
            self.pattern_vars[key].set(getattr(patterns, key))
        self.refresh()

    def refresh(self) -> bool:
        """Re-scan the folder and redraw every view. Nothing is moved."""

        if self.directory is None:
            self._remember_status(lambda: (t("choose_status"), False))
            return False
        try:
            params = self.read_params()
            patterns = self.read_patterns()
        except ValueError as exc:
            message = str(exc)
            self._remember_status(lambda message=message: (t("options_error", message=message), True))
            return False
        try:
            result = cluster_directory(self.directory, params, patterns)
        except OSError as exc:
            path, error = self.directory, exc
            self._remember_status(
                lambda path=path, error=error: (t("could_not_read", path=path, error=error), True)
            )
            return False
        self._show_result(result)
        return True

    def select_cluster(self, index: int | None, show_day: bool = True) -> None:
        if self.result is None or index is None or not 0 <= index < len(self.result.clusters):
            return
        self.selected_cluster = index
        cluster = self.result.clusters[index]
        self.overview.select(index)
        self.day_view.select(index, scroll=False)
        self.calendar.select_cluster(index)
        if self.cluster_tree.selection() != (str(index),):
            self.cluster_tree.selection_set(str(index))
        self.cluster_tree.see(str(index))
        if show_day:
            self.show_day(cluster.start.date())

    def show_day(self, day: date) -> None:
        self.selected_day = day
        self.calendar.select_day(day)
        clusters = self.result.clusters if self.result else ()
        start = datetime.combine(day, time())
        self.day_view.show(clusters, start, start + timedelta(days=1))
        if self.selected_cluster is not None:
            self.day_view.select(self.selected_cluster, scroll=False)
        entries = self.files_by_day.get(day, [])
        self.day_tree.delete(*self.day_tree.get_children())
        for row, (item, index) in enumerate(entries):
            number = clusters[index].number
            self.day_tree.insert(
                "", "end", iid=str(row), values=(f"{item.timestamp:%H:%M:%S}", item.name, number)
            )
        count = file_count(len(entries))
        self.day_frame.configure(text=self._day_title(day, count))

    def apply_clustering(self) -> None:
        if self.directory is None or not self.refresh():
            return
        result = self.result
        assert result is not None
        if not result.clusters:
            messagebox.showinfo(t("nothing_to_move_title"), t("nothing_to_move_body"), parent=self.root)
            return
        already_clustered = any(
            is_cluster_folder_name(name) for name in result.ignored_directories
        )
        if already_clustered:
            prompt = t(
                "apply_update",
                path=self.directory,
                files=result.file_count,
                events=len(result.clusters),
            )
        else:
            prompt = t(
                "apply_create",
                events=len(result.clusters),
                path=self.directory,
                files=result.file_count,
            )
        confirmed = messagebox.askyesno(t("apply"), prompt, parent=self.root)
        if not confirmed:
            return
        try:
            move_into_cluster_folders(self.directory, result.clusters)
        except (OSError, ValueError) as exc:
            messagebox.showerror(t("could_not_move"), str(exc), parent=self.root)
            self.refresh()
            return
        files, events = result.file_count, len(result.clusters)
        messagebox.showinfo(t("applied_title"), t("applied_body", files=files, events=events), parent=self.root)
        self.apply_button.configure(state="disabled")
        self.flatten_button.configure(state="normal")
        self._remember_status(lambda: (t("preview_stays", files=files, events=events), False))

    def flatten_clustering(self) -> None:
        if self.directory is None or not self.directory.is_dir():
            return
        folders = [
            entry.name
            for entry in self.directory.iterdir()
            if entry.is_dir() and is_cluster_folder_name(entry.name)
        ]
        if not folders:
            messagebox.showinfo(
                t("nothing_to_flatten_title"), t("nothing_to_flatten_body"), parent=self.root
            )
            return
        confirmed = messagebox.askyesno(
            t("flatten"),
            t("flatten_confirm", folders=len(folders), path=self.directory),
            parent=self.root,
        )
        if not confirmed:
            return
        try:
            moved = flatten_cluster_folders(self.directory)
        except (OSError, ValueError) as exc:
            messagebox.showerror(t("could_not_flatten"), str(exc), parent=self.root)
            self.refresh()
            return
        messagebox.showinfo(
            t("flattened_title"), t("flattened_body", moved=moved, name=self.directory.name), parent=self.root
        )
        self.refresh()

    # ---- helpers ------------------------------------------------------------

    def _show_result(self, result: ClusterResult) -> None:
        self.result = result
        self.selected_cluster = None
        self.files_by_day = {}
        for index, cluster in enumerate(result.clusters):
            for item in cluster.files:
                self.files_by_day.setdefault(item.timestamp.date(), []).append((item, index))

        self.overview.show(result.clusters)
        self.calendar.set_clusters(result.clusters)

        self.cluster_tree.delete(*self.cluster_tree.get_children())
        for index, cluster in enumerate(result.clusters):
            self.cluster_tree.insert(
                "", "end", iid=str(index), values=(cluster.number, cluster.name, len(cluster.files))
            )

        self._fill_skipped(result)

        self.apply_button.configure(state="normal" if result.clusters else "disabled")
        clustered = any(is_cluster_folder_name(name) for name in result.ignored_directories)
        self.flatten_button.configure(state="normal" if clustered else "disabled")
        if result.clusters:
            self.show_day(result.clusters[0].start.date())
        else:
            self.day_view.show(())
            self.day_tree.delete(*self.day_tree.get_children())
            self.day_frame.configure(text=t("day_detail"))
        self._remember_status(lambda result=result: (self._summary(result), False))

    def _set_status(self, message: str, error: bool = False) -> None:
        self.status_text.set(message)
        self.status.configure(style="Error.TLabel" if error else "Status.TLabel")

    def _remember_status(self, builder) -> None:
        self._status_builder = builder
        message, error = builder()
        self._set_status(message, error)

    def _text(self, widget, key: str):
        widget._i18n_key = key
        widget.configure(text=t(key))
        self._bound.append(widget)
        return widget

    def _add_tab(self, tab: ttk.Frame, key: str) -> None:
        self.notebook.add(tab, text=t(key))
        self._tab_keys.append(key)

    def _fill_about(self) -> None:
        text = self.about_text
        text.configure(state="normal")
        text.delete("1.0", "end")
        for heading, body in sections():
            text.insert("end", heading + "\n", "heading")
            text.insert("end", body + "\n")
        text.configure(state="disabled")

    def _language_changed(self, _event: tk.Event | None = None) -> None:
        chosen = self.language_var.get()
        code = next((code for code, name in LANGUAGES if name == chosen), "en")
        set_language(code)
        self.retranslate()

    def retranslate(self) -> None:
        """Apply the current catalog to the window without scanning the folder again."""

        self.root.title(t("app_title"))
        for widget in self._bound:
            widget.configure(text=t(widget._i18n_key))
        for widget, example, groups_key in self._pattern_hints:
            widget.configure(text=f"{example}  ·  {t(groups_key)}")
        for index, key in enumerate(self._tab_keys):
            self.notebook.tab(index, text=t(key))
        for tree, columns in self._headings:
            for column, key in columns:
                tree.heading(column, text=t(key))
        self._fill_about()
        self.overview.set_placeholder(t("placeholder_timeline"))
        self.overview.retranslate()
        self.day_view.set_placeholder(t("placeholder_day"))
        self.day_view.retranslate()
        theme.use_script(self.root, self.fonts, language())
        self.calendar.redraw()
        if self.directory is None:
            self.folder_text.set(t("no_folder"))
        if self.result is not None:
            self._fill_skipped(self.result)
            if self.selected_day is not None:
                count = file_count(len(self.files_by_day.get(self.selected_day, [])))
                self.day_frame.configure(text=self._day_title(self.selected_day, count))
            else:
                self.day_frame.configure(text=t("day_detail"))
        message, error = self._status_builder()
        self._set_status(message, error)

    def _day_title(self, day: date, count: str) -> str:
        when = t(
            "date_long",
            weekday=t(f"wd_{day.weekday()}"),
            day=day.day,
            month=t(f"month_{day.month}"),
            year=day.year,
        )
        return t("day_heading", when=when, count=count)

    def _fill_skipped(self, result: ClusterResult) -> None:
        self.skipped_tree.delete(*self.skipped_tree.get_children())
        for name in result.ignored_directories:
            reason = t("reason_event" if is_cluster_folder_name(name) else "reason_subfolder")
            self.skipped_tree.insert("", "end", values=(name, reason))
        for name in result.ignored_without_timestamp:
            self.skipped_tree.insert("", "end", values=(name, t("reason_no_timestamp")))

    def _summary(self, result: ClusterResult) -> str:
        event_folders = [name for name in result.ignored_directories if is_cluster_folder_name(name)]
        other_folders = [name for name in result.ignored_directories if name not in event_folders]
        included = t("event_folders_included", n=len(event_folders)) if event_folders else ""
        return t(
            "status_summary",
            events=len(result.clusters),
            files=result.file_count,
            missing=len(result.ignored_without_timestamp),
            included=included,
            folders=len(other_folders),
            model=_describe_model(result.model),
        )

    def _tree_selected(self, event: tk.Event | None = None) -> None:
        selection = self.cluster_tree.selection()
        if selection and int(selection[0]) != self.selected_cluster:
            self.select_cluster(int(selection[0]))

    def _day_clicked(self, day: date) -> None:
        self.show_day(day)
        info = self.calendar.days.get(day)
        if info is not None and info.cluster is not None:
            self.select_cluster(info.cluster, show_day=False)

    def _timeline_clicked(self, when: datetime) -> None:
        self._day_clicked(when.date())

    def _install_icon(self) -> None:
        """Use the PNG raster of ``icon.svg``. Tk does not load SVG or ICO here."""

        try:
            self._icon = tk.PhotoImage(file=str(_icon_path()))
        except tk.TclError:
            return
        self.root.iconphoto(True, self._icon)


def _describe_model(model) -> str:
    if model is None:
        return t("model_none", name=MODEL_NAME)
    if not model.separated:
        return t("model_one", name=MODEL_NAME)
    return t("model_learned", hours=f"{model.boundary_hours:.0f}", name=MODEL_NAME)


def _icon_path() -> Path:
    """PNG raster of ``ui/assets/icon.svg``, which Tk can load as the window icon."""

    return Path(__file__).resolve().parent / "assets" / "icon.png"


def main() -> int:
    root = tk.Tk()
    ClusterApp(root)
    root.mainloop()
    return 0
