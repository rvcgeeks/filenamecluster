"""The window: the header, the tabs, and switching language.

The controller decides what a click does. Each tab owns its widgets.
``AppView`` puts them on one ``tk.Tk`` and forwards a click by name.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import sys
import tkinter as tk
from tkinter import ttk

from filenamecluster.log import trace_module
from filenamecluster.ui.controller import ActionsPort, Wait
from . import theme
from .clusters_tab import ClustersTab
from .columns import EqualColumns
from .dialogs import Dialogs
from .i18n import LANGUAGES, t
from .info_tabs import InfoTabs
from .messages import Messages
from .options_tab import OptionsTab
from .pattern_table import PatternTable
from .forwarding import ViewForwarding
from .render import show_current, show_topic
from .runner import DiskRunner
from .widgets import WidgetKit


class AppView(ViewForwarding):
    """Widgets for one ``tk.Tk``. ``bind`` attaches actions before ``build``."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.actions: ActionsPort | None = None
        self.model = None
        self.fonts = theme.apply(root)
        self.bound: list[ttk.Widget] = []
        self.tab_keys: list[str] = []
        self.headings: list[tuple[ttk.Treeview, tuple[tuple[str, str], ...]]] = []
        self.inputs_locked = False
        self.options_user_sized = False
        self.placing_columns = False
        self.equal_columns_job: str | None = None
        self.options_columns = None
        self.folder_text = tk.StringVar(root, self.translate("no_folder"))
        self.input_text = tk.StringVar(root, self.translate("input_same"))
        self.status_text = tk.StringVar(root, self.translate("choose_status"))
        self.language_var = tk.StringVar(
            root, next(name for code, name in LANGUAGES if code == "en")
        )
        self.logging_var = tk.BooleanVar(root, False)
        self.dialogs = Dialogs(root, self.translate)
        self.kit = WidgetKit(self)
        self.messages = Messages(self)
        self.clusters = ClustersTab(self, self.kit)
        self.patterns = PatternTable(self, self.kit)
        self.columns = EqualColumns(self)
        self.options = OptionsTab(self, self.kit)
        self.info = InfoTabs(self, self.kit)
        self.runner = DiskRunner(root, self.translate)

    def bind(self, actions: ActionsPort) -> None:
        """Attach the actions a click reports to. The view does not import that class."""

        self.actions = actions

    def attach(self, model) -> None:
        """Keep the model and subscribe. ``draw`` paints it after the widgets exist."""

        self.model = model
        model.listen(self._on_session)

    def draw(self) -> None:
        """Paint the attached model once the widgets exist."""

        show_current(self, self.model)

    def _on_session(self, topic) -> None:
        show_topic(self, self.model, topic)

    def request_refresh(self) -> None:
        self.flush_edits()
        self.actions.refresh()

    def request_defaults(self) -> None:
        self.flush_edits()
        self.actions.restore_defaults()

    def request_apply(self) -> None:
        self.flush_edits()
        self.actions.apply_clustering()

    def request_flatten(self) -> None:
        self.flush_edits()
        self.actions.flatten_clustering()

    def request_add_pattern(self) -> None:
        self.flush_edits()
        self.actions.add_pattern_rule()

    def request_remove_pattern(self) -> None:
        self.flush_edits()
        self.actions.remove_pattern_rule(self.patterns.selected_ids())

    def build(self) -> None:
        """Create the header, the status line, and the four tabs."""

        if self.actions is None:
            raise RuntimeError("controller is not attached")
        root = self.root
        root.title(self.translate("app_title"))
        root.geometry("1360x880")
        root.minsize(1040, 680)
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.kit.install_icon()
        self._build_header()
        self.status = ttk.Label(root, textvariable=self.status_text, style="Status.TLabel")
        self.status.pack(fill="x", side="bottom", pady=(8, 0))
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=(8, 0))
        self.clusters.build()
        self.options.build()
        self.info.build_skipped()
        self.info.build_about()
        self._publish()
        if self.model is None:
            raise RuntimeError("model is not attached")
        self.root.after_idle(self.finish_equal_columns)

    def _publish(self) -> None:
        """Names tests and the painter use for widgets that a section created."""

        self.cluster_tree = self.clusters.cluster_tree
        self.overview = self.clusters.overview
        self.calendar = self.clusters.calendar
        self.day_view = self.clusters.day_view
        self.day_tree = self.clusters.day_tree
        self.day_frame = self.clusters.day_frame
        self.pattern_tree = self.patterns.pattern_tree
        self.option_vars = self.options.option_vars
        self.limit_vars = self.options.limit_vars
        self.option_inputs = self.options.option_inputs
        self.limit_inputs = self.options.limit_inputs
        self.logging_switch = self.options.logging_switch
        self.model_tree = self.options.model_tree
        self.options_rows = self.options.options_rows
        self.skipped_tree = self.info.skipped_tree
        self.about_text = self.info.about_text

    def set_folder(self, path: str) -> None:
        self.folder_text.set(path)
        incoming = None if self.model is None else self.model.input_directory
        if incoming is None:
            self.input_text.set(self.translate("input_same"))
        else:
            self.input_text.set(self.translate("input_path", path=incoming))

    def translate(self, key: str, **fields: object) -> str:
        """Translate from the model's authoritative language."""

        code = self.model.language if self.model is not None else "en"
        return t(key, code=code, **fields)

    def set_actions(self, *, apply: bool, flatten: bool) -> None:
        self.apply_button.configure(state="normal" if apply else "disabled")
        self.flatten_button.configure(state="normal" if flatten else "disabled")

    def set_busy(self, busy: bool) -> None:
        if busy and not self.inputs_locked:
            self.lock_inputs()
        elif not busy and self.inputs_locked:
            self.unlock_inputs()

    def run_work(self, wait: Wait, work, on_done) -> None:
        """Run disk work under the spinner. Tests may replace this method."""

        self.runner.start(self.messages.wait_key(wait), work, on_done)

    def language_code(self) -> str:
        chosen = self.language_var.get()
        return next((code for code, name in LANGUAGES if name == chosen), "en")

    def use_language(self, code: str) -> None:
        """Switch the catalog and redraw the words already on screen."""

        chosen = next((name for item, name in LANGUAGES if item == code), "English")
        if self.language_var.get() != chosen:
            self.language_var.set(chosen)
        self.retranslate()

    def retranslate(self) -> None:
        """Apply the current catalog, then draw the session again."""

        self.root.title(self.translate("app_title"))
        for widget in self.bound:
            widget.configure(text=self.translate(widget._i18n_key))
        for index, key in enumerate(self.tab_keys):
            self.notebook.tab(index, text=self.translate(key))
        for tree, columns in self.headings:
            for column, key in columns:
                tree.heading(column, text=self.translate(key))
        self.info.fill_about()
        self.overview.set_placeholder(self.translate("placeholder_timeline"))
        self.overview.retranslate()
        self.day_view.set_placeholder(self.translate("placeholder_day"))
        self.day_view.retranslate()
        theme.use_script(self.root, self.fonts, self.model.language)
        self.calendar.redraw()
        if self.model is not None and self.model.directory is None:
            self.folder_text.set(self.translate("no_folder"))
        if self.model is not None:
            show_current(self, self.model)

    def _on_language(self, _event: object | None = None) -> None:
        self.actions.language_chosen(self.language_code())

    def _build_header(self) -> None:
        header = ttk.Frame(self.root, style="Header.TFrame", padding=(16, 12))
        header.pack(fill="x")
        text = ttk.Frame(header, style="Header.TFrame")
        text.pack(side="left", fill="x", expand=True)
        self.kit.text(ttk.Label(text, style="Title.TLabel"), "app_title").pack(anchor="w")
        ttk.Label(text, textvariable=self.folder_text, style="Path.TLabel").pack(anchor="w")
        ttk.Label(text, textvariable=self.input_text, style="Path.TLabel").pack(anchor="w")
        self.apply_button = self.kit.text(
            ttk.Button(header, style="Accent.TButton", command=self.request_apply, state="disabled"),
            "apply",
        )
        self.apply_button.pack(side="right")
        self.flatten_button = self.kit.text(
            ttk.Button(header, command=self.request_flatten, state="disabled"),
            "flatten",
        )
        self.flatten_button.pack(side="right", padx=(0, 8))
        self.kit.text(ttk.Button(header, command=self.actions.choose_folder), "choose_folder").pack(
            side="right", padx=8
        )
        self.kit.text(ttk.Button(header, command=self.actions.choose_input), "choose_input").pack(
            side="right"
        )
        self.kit.text(ttk.Button(header, command=self.actions.clear_input), "clear_input").pack(
            side="right", padx=(0, 8)
        )
        language_box = ttk.Combobox(
            header,
            textvariable=self.language_var,
            values=[name for _code, name in LANGUAGES],
            state="readonly",
            width=12,
        )
        language_box.pack(side="right")
        language_box.bind("<<ComboboxSelected>>", self._on_language)
        self.kit.text(ttk.Label(header, style="Header.TLabel"), "language").pack(side="right", padx=(0, 6))


trace_module(sys.modules[__name__])
