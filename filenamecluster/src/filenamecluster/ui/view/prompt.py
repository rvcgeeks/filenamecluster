"""Apply and Flatten prompts that accept themselves after a short wait.

``PROMPT_TIMEOUT_SECONDS`` is the wait. Change that one number to change
every confirmation and OK prompt in those two flows.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import sys
import tkinter as tk
from tkinter import ttk

from filenamecluster.log import trace_module
from . import theme

PROMPT_TIMEOUT_SECONDS = 30


def countdown_step(left: int) -> tuple[int, bool]:
    """One second later. True means the wait ran out, which answers OK."""

    left -= 1
    return left, left <= 0


def closed_answer(cancel: str | None) -> bool:
    """Closing a question is Cancel. Closing an OK-only prompt is OK."""

    return cancel is None


def yes_no(
    parent: tk.Misc,
    title: str,
    body: str,
    *,
    ok: str,
    cancel: str | None,
    countdown: str,
    timeout: int,
) -> bool:
    """Wait for OK or Cancel. The timer running out is OK.

    ``cancel`` is ``None`` when the dialog only dismisses. Closing a question
    is Cancel. Closing an OK-only prompt is OK.
    """

    answered = {"ok": True}
    window = tk.Toplevel(parent)
    window.title(title)
    window.withdraw()
    window.transient(parent)
    window.resizable(False, False)
    window.configure(background=theme.BACKGROUND)
    left = max(int(timeout), 0)

    def finish(accepted: bool) -> None:
        answered["ok"] = accepted
        try:
            window.destroy()
        except tk.TclError:
            pass

    window.protocol("WM_DELETE_WINDOW", lambda: finish(closed_answer(cancel)))
    frame = ttk.Frame(window, padding=theme.px(16))
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text=body, wraplength=theme.px(420), justify="left").pack(anchor="w")
    timer = ttk.Label(frame, text=countdown.format(seconds=left))
    timer.pack(anchor="w", pady=(theme.px(12), theme.px(12)))
    buttons = ttk.Frame(frame)
    buttons.pack(fill="x")
    ttk.Button(buttons, text=ok, command=lambda: finish(True)).pack(side="left")
    if cancel is not None:
        ttk.Button(buttons, text=cancel, command=lambda: finish(False)).pack(
            side="left", padx=(theme.px(8), 0)
        )

    def tick() -> None:
        nonlocal left
        if not window.winfo_exists():
            return
        left, expired = countdown_step(left)
        if expired:
            finish(True)
            return
        timer.configure(text=countdown.format(seconds=left))
        window.after(1000, tick)

    if left <= 0:
        finish(True)
        return True
    window.update_idletasks()
    width = window.winfo_reqwidth()
    height = window.winfo_reqheight()
    x = parent.winfo_rootx() + max(0, (parent.winfo_width() - width) // 2)
    y = parent.winfo_rooty() + max(0, (parent.winfo_height() - height) // 2)
    window.geometry(f"+{x}+{y}")
    window.deiconify()
    window.lift()
    window.focus_set()
    window.grab_set()
    window.after(1000, tick)
    window.wait_window()
    return answered["ok"]


trace_module(sys.modules[__name__])
