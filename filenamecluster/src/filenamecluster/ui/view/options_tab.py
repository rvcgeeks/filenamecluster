"""The Options tab: patterns, safety limits, years, and the learned-model table.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import sys
import tkinter as tk
from tkinter import ttk

from filenamecluster.log import trace_module

_MEANING = {
    "within_hours": "model_within",
    "between_hours": "model_between",
    "boundary_hours": "model_boundary",
    "separated": "model_separated",
}


class OptionsTab:
    """Lay out the option fields and report their text. The controller stores it."""

    def __init__(self, host, kit) -> None:
        self.host = host
        self.kit = kit
        self._suppress_fields = False
        self._suppress_logging = False

    def build(self) -> None:
        tab = ttk.Frame(self.host.notebook, padding=(10, 10, 10, 6))
        self.kit.add_tab(tab, "tab_options")
        self.host.options_user_sized = False
        self.host.placing_columns = False
        self.host.equal_columns_job = None

        buttons = ttk.Frame(tab)
        buttons.pack(side="bottom", fill="x", pady=(8, 0))
        self.kit.text(
            ttk.Button(buttons, style="Accent.TButton", command=self.host.request_refresh),
            "update_preview",
        ).pack(side="left")
        self.kit.text(
            ttk.Button(buttons, command=self.host.request_defaults), "restore_defaults"
        ).pack(side="left", padx=8)
        self.logging_switch = self.kit.text(
            ttk.Checkbutton(buttons, variable=self.host.logging_var, command=self.on_logging),
            "write_log",
        )
        self.logging_switch.pack(side="right")

        rows = self.kit.split(tab, "vertical")
        rows.pack(fill="both", expand=True)
        self.options_rows = rows
        self.host.patterns.build(rows)

        columns = self.kit.split(rows, "horizontal")
        self.host.options_columns = columns
        rows.add(columns, stretch="always", minsize=160)

        self._suppress_fields = True
        self.option_vars = {
            key: tk.StringVar(self.host.root, "")
            for key, *_rest in self.host.hour_fields
        }
        self.limit_vars = {
            key: tk.StringVar(self.host.root, "")
            for key, *_rest in self.host.limit_fields
        }
        gaps = self.kit.text(ttk.LabelFrame(columns, padding=8), "safety_limits")
        self.option_inputs: dict[str, ttk.Spinbox] = {}
        for row, (key, label_key, hint_key, bounds) in enumerate(self.host.hour_fields):
            low, high, step = bounds
            self.option_inputs[key] = self.kit.option_row(
                gaps, row, label_key, hint_key, self.option_vars[key], low, high, step
            )
            self._watch_field("hour", key)
        self.kit.reflow(gaps)
        columns.add(gaps, stretch="always", minsize=160, width=240, sticky="nsew")

        limits = self.kit.text(ttk.LabelFrame(columns, padding=8), "years_frame")
        self.limit_inputs: dict[str, ttk.Spinbox] = {}
        for row, (key, _label, _hint, low, high) in enumerate(self.host.limit_fields):
            self.limit_inputs[key] = self.kit.option_row(
                limits, row, f"limit_{key}", f"limit_{key}_hint", self.limit_vars[key], low, high, 1
            )
            self._watch_field("limit", key)
        self._suppress_fields = False
        self.kit.reflow(limits)
        columns.add(limits, stretch="always", minsize=160, width=240, sticky="nsew")

        model = self.kit.text(ttk.LabelFrame(columns, padding=8), "model_frame")
        self.kit.flowing_help(model, "model_help")
        self.model_tree = self.kit.tree(
            model,
            (
                ("parameter", "col_parameter", 140, "w"),
                ("value", "col_value", 110, "w"),
                ("meaning", "col_meaning", 160, "w"),
            ),
        )
        self.model_tree.configure(height=4)
        self.show_learned(())
        columns.add(model, stretch="always", minsize=160, width=240, sticky="nsew")
        columns.bind("<Configure>", self.host.columns.balance)
        columns.bind("<ButtonPress-1>", self.host.columns.mark_user_sized, add="+")

    def show_values(
        self,
        options: dict[str, str],
        limits: dict[str, str],
    ) -> None:
        self._suppress_fields = True
        try:
            for key, value in options.items():
                self.option_vars[key].set(value)
            for key, value in limits.items():
                self.limit_vars[key].set(value)
        finally:
            self._suppress_fields = False

    def show_logging(self, enabled: bool) -> None:
        if bool(self.host.logging_var.get()) == bool(enabled):
            return
        self._suppress_logging = True
        try:
            self.host.logging_var.set(bool(enabled))
        finally:
            self._suppress_logging = False

    def on_logging(self) -> None:
        if self._suppress_logging:
            return
        self.host.actions.logging_chosen(bool(self.host.logging_var.get()))

    def show_learned(self, cells) -> None:
        """``cells`` are ``(key, value)``. ``None`` is the not-loaded mark."""

        self.model_tree.delete(*self.model_tree.get_children())
        for key, value in cells:
            shown = (
                self.host.translate("model_value_pending")
                if value is None
                else value
            )
            self.model_tree.insert(
                "",
                "end",
                iid=key,
                values=(
                    f"learned.{key}",
                    shown,
                    self.host.translate(_MEANING[key]),
                ),
            )

    def _watch_field(self, kind: str, key: str) -> None:
        variable = self.option_vars[key] if kind == "hour" else self.limit_vars[key]
        variable.trace_add("write", lambda *_args, kind=kind, key=key: self._report_variable(kind, key))
        widget = self.option_inputs[key] if kind == "hour" else self.limit_inputs[key]
        widget.bind("<KeyRelease>", lambda _event, kind=kind, key=key: self._report_raw(kind, key), add="+")

    def _report_variable(self, kind: str, key: str) -> None:
        if self._suppress_fields or self.host.actions is None:
            return
        variable = self.option_vars[key] if kind == "hour" else self.limit_vars[key]
        widget = self.option_inputs[key] if kind == "hour" else self.limit_inputs[key]
        try:
            text = str(variable.get())
        except tk.TclError:
            text = widget.get()
        self._store_field(kind, key, text)

    def _report_raw(self, kind: str, key: str) -> None:
        if self._suppress_fields or self.host.actions is None:
            return
        widget = self.option_inputs[key] if kind == "hour" else self.limit_inputs[key]
        self._store_field(kind, key, widget.get())

    def _store_field(self, kind: str, key: str, text: str) -> None:
        if kind == "hour":
            self.host.actions.revise_option(key, text)
        else:
            self.host.actions.revise_limit(key, text)


trace_module(sys.modules[__name__])
