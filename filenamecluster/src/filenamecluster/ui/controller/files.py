"""Open a file or an event folder with the operating system.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from filenamecluster.core.organize import _source_path
from filenamecluster.core.parse import TimestampedFile
from filenamecluster.log import event, trace_module


def openable_file(directory: Path, item: TimestampedFile, cluster_name: str) -> Path | None:
    """Where the file sits now, including an event folder created by Apply."""

    try:
        current = _source_path(directory, item, item.name)
    except ValueError:
        return None
    if current.is_file():
        return current
    if not cluster_name:
        return None
    try:
        placed = _source_path(
            directory,
            TimestampedFile(item.name, item.timestamp, source=f"{cluster_name}/{item.name}"),
            item.name,
        )
    except ValueError:
        return None
    if placed.is_file():
        return placed
    return None


def open_file(path: Path) -> None:
    """Open ``path`` with the operating system's default application."""

    target = str(Path(path))
    event("file_open", path=target)
    if sys.platform == "darwin":
        subprocess.Popen(["open", target])
    elif sys.platform == "win32":
        os.startfile(target)
    else:
        subprocess.Popen(["xdg-open", target])


def open_folder_window(path: Path) -> None:
    """Open ``path`` in a new file-manager window."""

    folder = str(Path(path))
    event("folder_open", path=folder)
    if sys.platform == "darwin":
        escaped = folder.replace("\\", "\\\\").replace('"', '\\"')
        subprocess.Popen(
            [
                "osascript",
                "-e",
                f'tell application "Finder" to make new Finder window to (POSIX file "{escaped}")',
                "-e",
                'tell application "Finder" to activate',
            ]
        )
    elif sys.platform == "win32":
        subprocess.Popen(["explorer", folder])
    else:
        subprocess.Popen(["xdg-open", folder])


trace_module(sys.modules[__name__])
