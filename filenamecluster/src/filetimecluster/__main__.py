"""Start the Tkinter window.

``uv run filetimecluster`` and ``python -m filetimecluster`` both call
``filetimecluster.ui.app.main``. PyInstaller freezes this file.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Introduction: ``readme.md``.
"""

from filetimecluster.ui.app import main

if __name__ == "__main__":
    raise SystemExit(main())
