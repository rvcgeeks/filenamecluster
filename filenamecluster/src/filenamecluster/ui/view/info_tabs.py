"""The Skipped and About tabs.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import sys
import tkinter as tk
from tkinter import ttk

from filenamecluster.log import trace_module
from filenamecluster.ui.model import SkippedReason
from . import theme
from .about import sections

_REASON_KEYS = {
    SkippedReason.EVENT_FOLDER: "reason_event",
    SkippedReason.SUBFOLDER: "reason_subfolder",
    SkippedReason.NO_TIMESTAMP: "reason_no_timestamp",
}


class InfoTabs:
    """List what a scan skipped, and show the About text."""

    def __init__(self, host, kit) -> None:
        self.host = host
        self.kit = kit

    def build_skipped(self) -> None:
        tab = ttk.Frame(self.host.notebook, padding=10)
        self.kit.add_tab(tab, "tab_skipped")
        self.kit.text(ttk.Label(tab, style="Muted.TLabel"), "skipped_intro").pack(anchor="w", pady=(0, 6))
        self.skipped_tree = self.kit.tree(
            tab, (("name", "col_name", 480, "w"), ("reason", "col_reason", 260, "w"))
        )

    def build_about(self) -> None:
        tab = ttk.Frame(self.host.notebook, padding=10)
        self.kit.add_tab(tab, "tab_about")
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
            font=self.host.fonts["small"],
            spacing3=4,
        )
        bar = ttk.Scrollbar(tab, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=bar.set)
        bar.pack(side="right", fill="y")
        text.pack(fill="both", expand=True)
        text.tag_configure(
            "heading",
            font=self.host.fonts["heading"],
            foreground=theme.ACCENT_ACTIVE,
            spacing1=12,
            spacing3=6,
        )
        self.about_text = text
        self.fill_about()

    def show_skipped(self, folders, files) -> None:
        """``folders`` and ``files`` are ``(name, reason_key)`` pairs."""

        rows = tuple(
            (name, self.host.translate(_REASON_KEYS[reason]))
            for name, reason in tuple(folders) + tuple(files)
        )
        self.kit.fill_tree(self.skipped_tree, rows)

    def fill_about(self) -> None:
        text = self.about_text
        text.configure(state="normal")
        text.delete("1.0", "end")
        for heading, body in sections(self.host.translate):
            text.insert("end", heading + "\n", "heading")
            text.insert("end", body + "\n")
        text.configure(state="disabled")


trace_module(sys.modules[__name__])
