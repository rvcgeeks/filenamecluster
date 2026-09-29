"""Finish the Mac app after Nuitka writes it."""

from __future__ import annotations

import plistlib
from pathlib import Path

from build.log import get_logger

log = get_logger(__name__)


def enable_retina(app: Path) -> bool:
    """Draw ``app`` at the screen's pixel density. False when there is no app."""

    plist_path = app / "Contents" / "Info.plist"
    log.debug("app %s plist %s", app, plist_path)
    if not plist_path.is_file():
        log.debug("no Info.plist, leaving the app unchanged")
        return False
    info = plistlib.loads(plist_path.read_bytes())
    log.debug("Info.plist keys before %s", sorted(info))
    info["NSHighResolutionCapable"] = True
    plist_path.write_bytes(plistlib.dumps(info))
    log.debug("NSHighResolutionCapable true")
    return True
