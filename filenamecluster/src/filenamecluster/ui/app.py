"""Compose the model, the view, and the controller, then start the window.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Introduction: ``readme.md``. Mathematics: ``docs/algorithm.md``.
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import sys
import tkinter as tk

from filenamecluster.log import configure, event, log_call, trace_module
from filenamecluster.ui.controller.actions import AppController
from filenamecluster.ui.model.session import AppModel
from filenamecluster.ui.view.theme import prepare_process_dpi
from filenamecluster.ui.view.window import AppView

__all__ = ["FileNameClusterApp", "main"]


class FileNameClusterApp:
    """One window. Attribute lookup continues into the controller, view, and model."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.model = AppModel()
        self.view = AppView(root, self.model)
        self.controller = AppController(self.model, self.view)
        self.view.controller = self.controller
        self.view.build()

    def __getattr__(self, name: str):
        for part in (self.controller, self.view, self.model):
            try:
                return getattr(part, name)
            except AttributeError:
                continue
        raise AttributeError(name)


def main() -> int:
    configure()
    event("application_start")
    log_call("filenamecluster.ui.view.theme.prepare_process_dpi")
    prepare_process_dpi()
    log_call("tkinter.Tk")
    root = tk.Tk()
    log_call("filenamecluster.ui.app.FileNameClusterApp")
    app = FileNameClusterApp(root)
    root.after_idle(app._finish_equal_columns)
    root.mainloop()
    return 0


trace_module(sys.modules[__name__])
