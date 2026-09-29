"""Compose the model, the view, and the controller, then start the window.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Introduction: ``readme.md``. Mathematics: ``docs/algorithm.md``.
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import sys
import tkinter as tk

from filenamecluster.log import configure, event, log_call, trace_module
from filenamecluster.core.parser import LIMIT_FIELDS
from filenamecluster.ui.controller import AppController, SystemFiles, SystemLogging
from filenamecluster.ui.model import AppModel, OptionFields
from filenamecluster.ui.view import AppView, prepare_process_dpi

__all__ = ["FileNameClusterApp", "main"]


class FileNameClusterApp:
    """One window: a session, the widgets, and the actions that connect them.

    ``disk`` runs folder work. When it is omitted, the window's spinner runs it.
    """

    def __init__(self, root: tk.Tk, disk=None) -> None:
        self.root = root
        self.model = AppModel()
        self.view = AppView(root)
        self.view.attach(self.model)
        self.controller = AppController(
            self.model,
            self.view,
            disk=disk,
            files=SystemFiles(),
            logging=SystemLogging(),
        )
        self.view.bind(self.controller)
        self.view.build(OptionFields.FIELDS, LIMIT_FIELDS)
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
