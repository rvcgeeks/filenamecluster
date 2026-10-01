"""Compose the model, the view, and the controller, then start the window.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Introduction: ``readme.md``. Mathematics: ``docs/algorithm.md``.
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import sys
import tkinter as tk

from filenamecluster.log import configure, event, log_call, trace_module
from filenamecluster.ui.controller import AppController
from filenamecluster.ui.model import AppModel
from filenamecluster.ui.view import AppView, prepare_process_dpi

__all__ = ["FileNameClusterApp", "main"]


class FileNameClusterApp:
    """One window: a session, the widgets, and the actions that connect them."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.model = AppModel()
        self.view = AppView(root)
        self.view.attach(self.model)
        self.controller = AppController(self.model, self.view)
        self.view.bind(self.controller)
        self.view.build()
        self.view.draw()


def main() -> int:
    configure()
    event("application_start")
    log_call("filenamecluster.ui.view.theme.prepare_process_dpi")
    prepare_process_dpi()
    log_call("tkinter.Tk")
    root = tk.Tk()
    log_call("filenamecluster.ui.app.FileNameClusterApp")
    FileNameClusterApp(root)
    root.mainloop()
    return 0


trace_module(sys.modules[__name__])
