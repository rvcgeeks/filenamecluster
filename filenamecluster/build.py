"""Build a native executable for the operating system this command runs on.

PyInstaller cannot cross-compile. ``uv run build`` makes a Mac app on a Mac,
a Linux binary on Linux, and a Windows binary on Windows.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Introduction: ``readme.md``.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT / "src" / "filetimecluster"
ANALYSIS = ROOT / "pyinstaller"


def main(argv: list[str] | None = None) -> int:
    """Freeze the app into ``dist/`` for this machine.

    PyInstaller's spec file and analysis folder are removed after a successful
    build. On a Mac the onedir copy beside ``filetimecluster.app`` is removed
    too; on Linux and Windows that folder is the program, so it stays.
    Pass ``--no-cleanup`` to keep everything for inspection.
    """

    args = list(sys.argv[1:] if argv is None else argv)
    keep_analysis = "--no-cleanup" in args
    args = [arg for arg in args if arg != "--no-cleanup"]
    if args:
        print(
            "uv run build makes an executable for this computer only.\n"
            "PyInstaller cannot cross-compile, so there is no Windows, Mac, or Linux option.\n"
            "Run the same command on the system you want a binary for.\n"
            "Pass --no-cleanup to keep the analysis files in pyinstaller/.",
            file=sys.stderr,
        )
        return 2

    entry = PACKAGE / "__main__.py"
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name",
        "filetimecluster",
        "--specpath",
        str(ANALYSIS),
        "--workpath",
        str(ANALYSIS / "work"),
        "--distpath",
        str(ROOT / "dist"),
        "--paths",
        str(ROOT / "src"),
    ]
    for path, destination in _bundled_files():
        command.extend(["--add-data", f"{path}{os.pathsep}{destination}"])
    command.append(str(entry))
    completed = subprocess.run(command, cwd=ROOT, check=False)
    if completed.returncode != 0:
        return completed.returncode
    print(f"Built for {sys.platform} in {ROOT / 'dist'}")
    if keep_analysis:
        print(f"Analysis kept in {ANALYSIS}")
        return 0
    shutil.rmtree(ANALYSIS, ignore_errors=True)
    print("Removed PyInstaller analysis files from pyinstaller/.")
    dist = ROOT / "dist"
    if (dist / "filetimecluster.app").is_dir():
        shutil.rmtree(dist / "filetimecluster", ignore_errors=True)
        print("Removed dist/filetimecluster; the Mac app is dist/filetimecluster.app.")
    return 0


def _bundled_files() -> list[tuple[Path, str]]:
    """JSON catalogs and the window icon, placed beside their modules."""

    files = [
        (path, "filetimecluster/ui/i18n")
        for path in sorted((PACKAGE / "ui" / "i18n").glob("*.json"))
    ]
    icon = PACKAGE / "ui" / "assets" / "icon.png"
    if icon.is_file():
        files.append((icon, "filetimecluster/ui/assets"))
    return files


if __name__ == "__main__":
    raise SystemExit(main())
