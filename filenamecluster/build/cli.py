"""``uv run python -m build [--no-cleanup]``."""

from __future__ import annotations

import platform
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from build.log import get_logger
from build.macos import enable_retina
from build.nuitka import NuitkaBuild
from build.paths import DIST, MAC_APP, ROOT
from build.tcl import MissingTclError, windows_bundle

log = get_logger(__name__)

NO_CLEANUP = "--no-cleanup"
USAGE = (
    "uv run python -m build makes an executable for this computer only.\n"
    "Nuitka compiles for the host, so there is no Windows, Mac, or Linux option.\n"
    "Run the same command on the system you want a binary for.\n"
    "Pass --no-cleanup to keep Nuitka's intermediate build files in dist/."
)


def main(argv: list[str] | None = None) -> int:
    """Compile the app into ``dist/`` for this machine and return the exit code."""

    args = list(sys.argv[1:] if argv is None else argv)
    log.debug("argv %s", args)
    log.debug("root %s", ROOT)
    log.debug("platform %s machine %s", sys.platform, platform.machine())
    log.debug("python %s executable %s", sys.version, sys.executable)
    log.debug("prefix %s base_prefix %s", sys.prefix, sys.base_prefix)
    keep_analysis = NO_CLEANUP in args
    log.debug("keep analysis %s", keep_analysis)
    if [arg for arg in args if arg != NO_CLEANUP]:
        log.error("%s", USAGE)
        print(USAGE, file=sys.stderr)
        return 2

    host = sys.platform
    nuitka = NuitkaBuild(host, keep_analysis)
    with TemporaryDirectory(prefix="filenamecluster-tcl-") as staging:
        log.debug("tcl staging %s", staging)
        extra: list[str] = []
        if host == "win32":
            try:
                bundle = windows_bundle(Path(staging))
            except MissingTclError as exc:
                log.error("%s", exc)
                print(exc, file=sys.stderr)
                return 1
            log.info("Tcl library %s", bundle.tcl)
            log.info("Tk library %s", bundle.tk)
            for package in bundle.packages:
                log.info("Tcl package %s", package)
            extra = bundle.nuitka_options()
            for option in extra:
                log.debug("nuitka tcl option %s", option)
        code = nuitka.run(extra)
    log.debug("nuitka exit %s", code)
    if code != 0:
        log.error("compile failed with exit %s", code)
        return code
    if host == "darwin":
        written = enable_retina(MAC_APP)
        log.info("high resolution app %s written %s", MAC_APP, written)
    log.info("built for %s in %s", host, DIST)
    if keep_analysis:
        log.info("intermediate files kept in %s", DIST)
    return 0
