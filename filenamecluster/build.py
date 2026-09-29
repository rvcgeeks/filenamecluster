"""Build a native executable for the operating system this command runs on.

Nuitka compiles for the host system. ``uv run python build.py`` makes a Mac app
on a Mac, a Linux binary on Linux, and a Windows binary on Windows.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Introduction: ``readme.md``.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT / "src" / "filenamecluster"


def main(argv: list[str] | None = None) -> int:
    """Compile the app into ``dist/`` for this machine.

    Windows writes ``dist/filenamecluster.exe`` and Linux writes
    ``dist/filenamecluster``, each as one file. Mac writes
    ``dist/filenamecluster.app``.
    Pass ``--no-cleanup`` to keep Nuitka's intermediate build files.
    """

    args = list(sys.argv[1:] if argv is None else argv)
    keep_analysis = "--no-cleanup" in args
    args = [arg for arg in args if arg != "--no-cleanup"]
    if args:
        print(
            "uv run python build.py makes an executable for this computer only.\n"
            "Nuitka compiles for the host, so there is no Windows, Mac, or Linux option.\n"
            "Run the same command on the system you want a binary for.\n"
            "Pass --no-cleanup to keep Nuitka's intermediate build files in dist/.",
            file=sys.stderr,
        )
        return 2

    assets = PACKAGE / "ui" / "assets"
    command = [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--assume-yes-for-downloads",
        "--enable-plugins=tk-inter",
        "--output-dir=dist",
        f"--include-data-dir={assets}=filenamecluster/ui/assets",
    ]
    if sys.platform == "darwin":
        command.extend(
            [
                "--macos-create-app-bundle",
                "--macos-app-name=filenamecluster",
                f"--macos-app-icon={assets / 'icon.png'}",
                "--disable-cache=ccache",
                "--output-filename=filenamecluster-bin",
                "--output-folder-name=filenamecluster",
            ]
        )
    else:
        command.extend(["--onefile", "--output-filename=filenamecluster"])
    if sys.platform == "win32":
        command.append("--windows-console-mode=disable")
    if not keep_analysis:
        command.append("--remove-output")
    command.extend(["--python-flag=-m", str(PACKAGE)])
    completed = subprocess.run(command, cwd=ROOT, check=False)
    if completed.returncode != 0:
        return completed.returncode
    _enable_retina_app()
    print(f"Built for {sys.platform} in {ROOT / 'dist'}")
    if keep_analysis:
        print(f"Intermediate files kept in {ROOT / 'dist'}")
    return 0


def _enable_retina_app() -> None:
    """Draw the frozen Mac app at the screen's pixel density."""

    plist_path = ROOT / "dist" / "filenamecluster.app" / "Contents" / "Info.plist"
    if not plist_path.is_file():
        return
    import plistlib

    info = plistlib.loads(plist_path.read_bytes())
    info["NSHighResolutionCapable"] = True
    plist_path.write_bytes(plistlib.dumps(info))


if __name__ == "__main__":
    raise SystemExit(main())
