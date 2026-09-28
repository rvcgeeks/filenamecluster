"""Start the Tkinter window.

``uv run filenamecluster`` and ``python -m filenamecluster`` both call
``filenamecluster.ui.app.main``. PyInstaller freezes this file.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Introduction: ``readme.md``.
"""

import sys
from filenamecluster.log import trace_module

from filenamecluster.ui.app import main

if __name__ == "__main__":
    raise SystemExit(main())

trace_module(sys.modules[__name__])
