"""Cluster camera-roll files into chronological events.

``filenamecluster.core`` holds the parsing, clustering, and moving logic.
``filenamecluster.ui`` is the Tkinter app started by ``uv run filenamecluster``.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Introduction: ``readme.md``. Mathematics: ``docs/algorithm.md``.
Design: ``docs/architecture.md``.
"""

import sys
from filenamecluster.log import trace_module

trace_module(sys.modules[__name__])
