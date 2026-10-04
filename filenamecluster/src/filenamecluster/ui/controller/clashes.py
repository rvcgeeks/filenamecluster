"""Walk destination-name clashes and collect replace or skip.

The view writes each answer onto a ``NameClash``. This class does not draw
and does not move a file.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

from filenamecluster.log import event, trace_module
from filenamecluster.ui.model import ClashChoice, NameClash
from .ports import DialogPort


class ClashResolver:
    """Ask once per clash, or once for all of them when the user says so."""

    def __init__(self, ui: DialogPort) -> None:
        self.ui = ui

    def replacing(self, clashes: Sequence, *, discard: bool = False) -> frozenset[Path] | None:
        """Source paths that may overwrite. ``None`` means the user closed the dialog.

        ``discard`` asks the window to delete a skipped source instead of leaving it.
        """

        if not clashes:
            return frozenset()
        chosen: list[Path] = []
        forced: ClashChoice | None = None
        remaining = len(clashes)
        for item in clashes:
            if forced is None:
                prompt = NameClash(name=item.target.name, count=remaining, discard=discard)
                self.ui.resolve_clash(prompt)
                if prompt.cancelled or prompt.choice is None:
                    event("name_clash_cancelled", name=item.target.name)
                    return None
                event(
                    "name_clash",
                    name=item.target.name,
                    choice=prompt.choice.name.lower(),
                    for_all=prompt.for_all,
                )
                if prompt.for_all:
                    forced = prompt.choice
                choice = prompt.choice
            else:
                choice = forced
            if choice is ClashChoice.REPLACE:
                chosen.append(item.source)
            remaining -= 1
        return frozenset(path.resolve() for path in chosen)


trace_module(sys.modules[__name__])
