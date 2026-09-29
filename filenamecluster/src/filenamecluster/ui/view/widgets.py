"""Widget helpers every tab of the window uses.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from filenamecluster.log import trace_module
from . import theme


def _icon_path() -> Path:
    """PNG raster of ``ui/assets/icon.svg``, which Tk can load as the window icon."""

    return Path(__file__).resolve().parents[1] / "assets" / "icon.png"


class WidgetKit:
    """Trees, labelled widgets, sashes, wrapping hints, and the input lock.

    ``host`` is the window. This class uses only the attributes it is given.
    """

    def __init__(self, host) -> None:
        self.host = host
        self._input_states: list[tuple[tk.Widget, str]] = []

    def tree(self, master: tk.Misc, columns: tuple) -> ttk.Treeview:
        frame = ttk.Frame(master)
        frame.pack(fill="both", expand=True, pady=(6, 0))
        tree = ttk.Treeview(
            frame, columns=[key for key, *_ in columns], show="headings", selectmode="browse"
        )
        for key, heading_key, width, anchor in columns:
            tree.heading(
                key,
                text=self.host.translate(heading_key),
                anchor=anchor,
            )
            tree.column(
                key,
                width=width,
                anchor=anchor,
                stretch=key in {"name", "pattern", "meaning", "parameter", "value"},
            )
        self.host.headings.append((tree, tuple((key, heading_key) for key, heading_key, *_rest in columns)))
        bar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=bar.set)
        tree.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")
        return tree

    def text(self, widget, key: str):
        widget._i18n_key = key
        widget.configure(text=self.host.translate(key))
        self.host.bound.append(widget)
        return widget

    def add_tab(self, tab: ttk.Frame, key: str) -> None:
        self.host.notebook.add(tab, text=self.host.translate(key))
        self.host.tab_keys.append(key)

    def split(self, master: tk.Misc, orient: str) -> tk.PanedWindow:
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

    def option_row(
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
        self.text(
            ttk.Label(frame, style="Info.TLabel", wraplength=200, justify="left"),
            label_key,
        ).grid(row=line, column=0, sticky="ew", pady=(4, 0))
        spin = ttk.Spinbox(frame, from_=low, to=high, increment=step, width=8, textvariable=variable)
        spin.grid(row=line, column=1, sticky="e", padx=(8, 0))
        spin.bind("<Return>", lambda _event: self.host.request_refresh())
        self.text(
            ttk.Label(frame, style="Muted.TLabel", wraplength=160, justify="left"),
            hint_key,
        ).grid(row=line + 1, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        frame.columnconfigure(0, weight=1)
        return spin

    def reflow(self, frame: ttk.LabelFrame) -> None:
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

    def flowing_help(self, frame: ttk.LabelFrame, key: str) -> None:
        label = self.text(
            ttk.Label(frame, style="Muted.TLabel", wraplength=280, justify="left"),
            key,
        )
        label.pack(anchor="w", fill="x", pady=(0, 6))

        def fit(event: tk.Event, label: ttk.Label = label) -> None:
            width = event.width - 20
            if width >= 80 and abs(int(label.cget("wraplength")) - width) >= 4:
                label.configure(wraplength=width)

        frame.bind("<Configure>", fit, add="+")

    def lock_inputs(self) -> None:
        """Disable buttons and option controls. Viewing the drawings stays possible."""

        self.host.patterns.flush_edits()
        self.host.inputs_locked = True
        locked: list[tuple[tk.Widget, str]] = []
        for widget in self._input_widgets():
            previous = str(widget.cget("state"))
            locked.append((widget, previous))
            widget.configure(state="disabled")
        self._input_states = locked

    def unlock_inputs(self) -> None:
        """Put buttons and option controls back to the states they had before the lock."""

        self.host.inputs_locked = False
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

        walk(self.host.root)
        return found

    def install_icon(self) -> None:
        """Use the PNG raster of ``icon.svg``. Tk does not load SVG or ICO here."""

        try:
            self._icon = tk.PhotoImage(file=str(_icon_path()))
        except tk.TclError:
            return
        self.host.root.iconphoto(True, self._icon)


trace_module(sys.modules[__name__])
