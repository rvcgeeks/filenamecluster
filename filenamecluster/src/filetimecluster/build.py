"""Console entry for ``uv run build``.

The build steps live in ``build.py`` beside ``pyproject.toml``.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Introduction: ``readme.md``.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


def main() -> int:
    """Run the project ``build.py`` and return its exit code."""

    script = Path(__file__).resolve().parents[2] / "build.py"
    if not script.is_file():
        print(f"Could not find {script}", file=sys.stderr)
        return 1
    try:
        runpy.run_path(str(script), run_name="__main__")
    except SystemExit as exit_:
        code = exit_.code
        if code is None:
            return 0
        if isinstance(code, int):
            return code
        print(code, file=sys.stderr)
        return 1
    return 0
