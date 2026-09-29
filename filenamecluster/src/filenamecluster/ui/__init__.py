"""Tkinter app: choose a folder, preview the clusters on a timeline, then apply.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Introduction: ``readme.md``. Mathematics: ``docs/algorithm.md``.
Design: ``docs/architecture.md``. The window icon is ``ui/assets/icon.svg``.
Visible strings are JSON catalogs in ``ui/assets/i18n``, loaded by ``ui/view/i18n``, for English, Hindi, Marathi, German, French, Japanese, and Korean. The window is ``app.py``. Drawing, theme, and layout live in ``view``. Session state lives in ``model``. Actions live in ``controller``.
"""

import sys
from filenamecluster.log import trace_module

trace_module(sys.modules[__name__])
