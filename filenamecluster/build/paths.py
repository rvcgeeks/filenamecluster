"""Where the build reads the package and writes the program."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "src" / "filenamecluster"
ASSETS = PACKAGE / "ui" / "assets"
DIST = ROOT / "dist"
MAC_APP = DIST / "filenamecluster.app"
