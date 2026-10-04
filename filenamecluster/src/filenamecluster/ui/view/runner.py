"""Progress bar and background thread for a folder read or a file move.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import sys
import threading
import tkinter as tk
from collections.abc import Callable

from filenamecluster.core.progress import Meter, bind
from filenamecluster.log import event, trace_module
from .progress_bar import ProgressDialog


class DiskRunner:
    """Show the progress bar and run work off the UI thread."""

    def __init__(self, root: tk.Misc, translate: Callable[..., str]) -> None:
        self._root = root
        self._translate = translate

    def start(self, message_key: str, work: Callable[[], object], on_done: Callable[[object], None]) -> None:
        """Start ``work`` on ``filenamecluster-disk`` and deliver the result on the UI thread."""

        root = self._root
        dialog = ProgressDialog(root, self._translate(message_key))
        root._filenamecluster_wait = dialog
        meter = Meter()
        outcome_box: dict[str, object] = {}
        event("disk_work", message=message_key)

        def worker() -> None:
            bind(meter)
            try:
                outcome_box["value"] = work()
            except Exception as exc:
                outcome_box["error"] = exc
            finally:
                outcome_box["done"] = True

        def poll() -> None:
            if getattr(root, "_filenamecluster_wait", None) is dialog:
                dialog.show(*meter.read())
            if not outcome_box.get("done"):
                root.after(50, poll)
                return
            error = outcome_box.get("error")
            try:
                on_done(error if error is not None else outcome_box.get("value"))
            finally:
                if getattr(root, "_filenamecluster_wait", None) is dialog:
                    root._filenamecluster_wait = None
                dialog.close()

        threading.Thread(target=worker, name="filenamecluster-disk", daemon=True).start()
        root.after(50, poll)


trace_module(sys.modules[__name__])
