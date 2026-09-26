"""Read and write the visible model file in the folder being clustered.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Mathematics: ``docs/algorithm.md``. Design: ``docs/architecture.md``.

The file is ``filetimecluster-model.json``, sitting next to the photos so it
can be opened and inspected. It records the boundary learned from timestamps.
It is not a hidden file.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from filetimecluster.core.learn import GapModel

MODEL_NAME = "filetimecluster-model.json"


@dataclass(frozen=True, slots=True)
class FolderModel:
    """The boundary last written for one folder."""

    learned: GapModel | None = None

    def with_learned(self, learned: GapModel | None) -> FolderModel:
        return FolderModel(learned)


def model_path(directory: Path | str) -> Path:
    return Path(directory) / MODEL_NAME


def load_model(directory: Path | str) -> FolderModel:
    """Load ``filetimecluster-model.json``, or an empty model when it is absent."""

    path = model_path(directory)
    if not path.is_file():
        return FolderModel()
    raw = json.loads(path.read_text(encoding="utf-8"))
    return FolderModel(learned=_learned(raw.get("learned")))


def save_model(directory: Path | str, model: FolderModel) -> Path:
    """Write the model where the user can see it, and return that path."""

    path = model_path(directory)
    document = {"learned": _learned_document(model.learned)}
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return path


def _learned(raw: object) -> GapModel | None:
    if not isinstance(raw, dict):
        return None
    try:
        return GapModel(
            within_hours=float(raw["within_hours"]),
            between_hours=float(raw["between_hours"]),
            boundary_hours=float(raw["boundary_hours"]),
            separated=bool(raw["separated"]),
        )
    except (KeyError, TypeError, ValueError):
        return None


def _learned_document(model: GapModel | None) -> dict | None:
    if model is None:
        return None
    return {
        "within_hours": model.within_hours,
        "between_hours": model.between_hours,
        "boundary_hours": model.boundary_hours,
        "separated": model.separated,
    }
