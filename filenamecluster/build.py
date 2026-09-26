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
PACKAGE = ROOT / "src" / "filenamecluster"
ANALYSIS = ROOT / "pyinstaller"


def main(argv: list[str] | None = None) -> int:
    """Freeze the app into ``dist/`` for this machine.

    Windows writes ``dist/filenamecluster.exe`` and Linux writes
    ``dist/filenamecluster``, each as one file. Mac writes
    ``dist/filenamecluster.app``. A Mac app bundle cannot be one file, so
    that build stays a folder inside the ``.app``.
    PyInstaller's spec file and analysis folder are removed after a successful
    build. On a Mac an extra folder beside the app is removed too.
    Pass ``--no-cleanup`` to keep the analysis files.
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
    ]
    # A Mac .app is a folder. One-file mode cannot wrap it, and PyInstaller 7
    # will reject that combination.
    if sys.platform != "darwin":
        command.append("--onefile")
    command.extend(
        [
            "--name",
            "filenamecluster",
            "--specpath",
            str(ANALYSIS),
            "--workpath",
            str(ANALYSIS / "work"),
            "--distpath",
            str(ROOT / "dist"),
            "--paths",
            str(ROOT / "src"),
        ]
    )
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
    extra = dist / "filenamecluster"
    if (dist / "filenamecluster.app").is_dir() and extra.is_dir():
        shutil.rmtree(extra)
        print("Removed dist/filenamecluster; the Mac app is dist/filenamecluster.app.")
    return 0


def _bundled_files() -> list[tuple[Path, str]]:
    """JSON catalogs and the window icon, placed beside their modules."""

    files = [
        (path, "filenamecluster/ui/i18n")
        for path in sorted((PACKAGE / "ui" / "i18n").glob("*.json"))
    ]
    icon = PACKAGE / "ui" / "assets" / "icon.png"
    if icon.is_file():
        files.append((icon, "filenamecluster/ui/assets"))
    return files


if __name__ == "__main__":
    raise SystemExit(main())
