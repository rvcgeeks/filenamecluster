"""Compile File Name Cluster into a native program for this computer.

``uv run python -m build``, run beside ``pyproject.toml``, calls
``build.cli.main``. Nuitka compiles for the host, so a Mac builds the Mac app,
Linux the Linux program, and Windows the Windows program.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Introduction: ``readme.md``.
"""

from build.cli import main
from build.macos import enable_retina
from build.nuitka import NuitkaBuild
from build.tcl import MissingTclError, PythonInstall, TclBundle, windows_bundle

__all__ = [
    "MissingTclError",
    "NuitkaBuild",
    "PythonInstall",
    "TclBundle",
    "enable_retina",
    "main",
    "windows_bundle",
]
