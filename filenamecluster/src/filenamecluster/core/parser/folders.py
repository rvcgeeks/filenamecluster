"""Recognise an event-folder name, including words added around its stamp.

The stamp is the chronological name Apply writes. Words before or after it
are a note. The dates in the stamp are not read back into times.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from filenamecluster.log import trace_module

_STAMP = (
    r"\d+ \d{2}-\d{2}-\d{4} \d{2}\.\d{2}\.\d{2} to "
    r"(?:\d{2}-\d{2}-\d{4} )?\d{2}\.\d{2}\.\d{2}"
)
_EVENT = re.compile(rf"^(?P<prefix>.*?)(?P<stamp>{_STAMP})(?P<suffix>.*)$")


def event_folder_parts(name: str) -> tuple[str, str, str] | None:
    """Prefix, stamp, and suffix. ``None`` when ``name`` is not an event folder."""

    if not name or name != Path(name).name or name in {".", ".."}:
        return None
    match = _EVENT.fullmatch(name.strip())
    if match is None:
        return None
    prefix, stamp, suffix = match.group("prefix", "stamp", "suffix")
    if prefix and not prefix[-1].isspace():
        return None
    if suffix and not suffix[0].isspace():
        return None
    return prefix.strip(), stamp, suffix.strip()


def is_cluster_folder_name(name: str) -> bool:
    """True when ``name`` is a folder this tool would create, plus any note."""

    return event_folder_parts(name) is not None


def folder_note(name: str) -> tuple[str, str] | None:
    """Words before and after the stamp, or ``None`` when there are none."""

    parts = event_folder_parts(name)
    if parts is None:
        return None
    prefix, _stamp, suffix = parts
    if not prefix and not suffix:
        return None
    return prefix, suffix


def name_with_note(prefix: str, stamp: str, suffix: str) -> str:
    """Put a note back around a stamp, skipping an empty side."""

    return " ".join(part for part in (prefix.strip(), stamp, suffix.strip()) if part)


trace_module(sys.modules[__name__])
