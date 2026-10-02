"""In-place rename of a cluster folder, with the original stamp locked.

The row is one line: words before the stamp, the stamp itself, then words
after it. The stamp is read-only so later calculations still see it.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import sys
import tkinter as tk
from tkinter import ttk

from filenamecluster.log import trace_module


class FolderNameEditor:
    """Right-click the Folder name cell and edit only the words around the stamp."""

    def __init__(self, host, tree: ttk.Treeview) -> None:
        self.host = host
        self.tree = tree
        self._frame: tk.Frame | None = None
        self.prefix: ttk.Entry | None = None
        self.stamp: ttk.Entry | None = None
        self.suffix: ttk.Entry | None = None
        self._index: int | None = None

    def bind(self) -> None:
        self.tree.bind("<Button-3>", self._right_click)
        self.tree.bind("<Button-2>", self._right_click)
        self.tree.bind("<Control-Button-1>", self._right_click)

    def close(self, save: bool) -> None:
        if self._frame is None:
            return
        if save:
            self.commit()
            return
        self._destroy()

    def begin(self, index: int) -> None:
        if self.host.inputs_locked or self.host.actions is None:
            return
        self.close(save=True)
        stamp = self.host.actions.cluster_stamp(index)
        if not stamp:
            return
        prefix, suffix = self.host.actions.cluster_note(index)
        tree = self.tree
        iid = str(index)
        if not tree.exists(iid):
            return
        tree.see(iid)
        tree.update_idletasks()
        x, y, width, height = tree.bbox(iid, "name") or (0, 0, 320, 24)
        frame = tk.Frame(tree, borderwidth=0)
        self.prefix = ttk.Entry(frame, width=14)
        self.stamp = ttk.Entry(frame, style="ClusterStamp.TEntry", takefocus=0)
        self.suffix = ttk.Entry(frame, width=14)
        self.prefix.insert(0, prefix)
        self.stamp.insert(0, stamp)
        self.stamp.configure(state="readonly")
        self.suffix.insert(0, suffix)
        self.prefix.grid(row=0, column=0, sticky="ew")
        self.stamp.grid(row=0, column=1)
        self.suffix.grid(row=0, column=2, sticky="ew")
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(2, weight=1)
        frame.update_idletasks()
        needed = (
            self.prefix.winfo_reqwidth()
            + self.stamp.winfo_reqwidth()
            + self.suffix.winfo_reqwidth()
            + 4
        )
        frame.place(x=x, y=y, width=max(width, needed), height=height)
        self._frame = frame
        self._index = index
        for entry in (self.prefix, self.suffix, self.stamp):
            entry.bind("<Return>", lambda _event: self.commit())
            entry.bind("<Escape>", self._cancel)
            entry.bind("<FocusOut>", self._focus_left)
        self.prefix.focus_set()
        self.prefix.select_range(0, "end")

    def commit(self) -> None:
        if self._frame is None or self.prefix is None or self.suffix is None:
            return
        prefix = self.prefix.get()
        suffix = self.suffix.get()
        index = self._index
        self._destroy()
        if index is not None and self.host.actions is not None:
            self.host.actions.rename_cluster_folder(index, prefix, suffix)

    def _cancel(self, _event: tk.Event | None = None) -> str:
        self._destroy()
        return "break"

    def _focus_left(self, _event: tk.Event | None = None) -> None:
        frame = self._frame
        if frame is None:
            return

        def finish() -> None:
            if self._frame is not frame:
                return
            try:
                focus = frame.focus_get()
            except tk.TclError:
                focus = None
            if focus in (self.prefix, self.stamp, self.suffix, frame):
                return
            self.commit()

        frame.after_idle(finish)

    def _right_click(self, event: tk.Event) -> str | None:
        if self.host.inputs_locked or self.host.actions is None:
            return None
        if self.tree.identify_column(event.x) != "#2":
            return None
        row = self.tree.identify_row(event.y)
        if not row or not str(row).isdigit():
            return None
        self.tree.selection_set(row)
        self.begin(int(row))
        return "break"

    def _destroy(self) -> None:
        frame = self._frame
        self._frame = None
        self.prefix = None
        self.stamp = None
        self.suffix = None
        self._index = None
        if frame is not None:
            frame.destroy()


trace_module(sys.modules[__name__])
