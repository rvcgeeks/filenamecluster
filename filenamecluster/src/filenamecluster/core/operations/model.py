"""Read and write ``filenamecluster-model.json``.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
The derivation is ``docs/algorithm.md``.

The file sits beside the photos. ``learned`` is the fitted boundary.
``options`` is the limits and filename rules last used. Options do not
change how the boundary is fitted.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Sequence
from pathlib import Path

from filenamecluster.core.algorithm.cluster import FolderModel, ModelOptions
from filenamecluster.core.algorithm.fit import GapModel
from filenamecluster.core.parser import MODEL_NAME
from filenamecluster.log import detail, event, trace_module


def model_path(directory: Path | str) -> Path:
    return Path(directory) / MODEL_NAME


def load_model(directory: Path | str) -> FolderModel:
    """Load ``filenamecluster-model.json``, or an empty model when it is absent."""

    path = model_path(directory)
    if not path.is_file():
        event("model_missing", path=str(path))
        return FolderModel()
    raw = json.loads(path.read_text(encoding="utf-8"))
    model = FolderModel(learned=_learned(raw.get("learned")), options=_options(raw.get("options")))
    event(
        "model_loaded",
        path=str(path),
        learned=model.learned is not None,
        options=model.options is not None,
    )
    if model.learned is not None:
        detail(
            "learned_loaded",
            within_hours=model.learned.within_hours,
            between_hours=model.learned.between_hours,
            boundary_hours=model.learned.boundary_hours,
            separated=model.learned.separated,
        )
    if model.options is not None:
        detail(
            "options_loaded",
            floor_hours=model.options.floor_hours,
            ceiling_hours=model.options.ceiling_hours,
            min_year=model.options.min_year,
            max_year=model.options.max_year,
            rules=len(model.options.rules),
        )
    return model


def save_model(directory: Path | str, model: FolderModel) -> Path:
    """Write the learned boundary and the options, and return that path."""

    path = model_path(directory)
    _write(
        path,
        {
            "learned": _learned_document(model.learned),
            "options": _options_document(model.options),
        },
    )
    event("model_saved", path=str(path), learned=model.learned is not None, options=model.options is not None)
    return path


def keep_rules(directory: Path | str, rows: Sequence[tuple[str, str, str, bool]]) -> None:
    """Replace ``options.rules`` in an existing model file. This is the other write.

    ``rows`` are ``(key, description, pattern, invalid)`` in table order.
    Nothing is written when every row compiles. ``"invalid": true`` is stored
    on the rows that do not, and the loader ignores that key.
    """

    if not any(invalid for _key, _description, _pattern, invalid in rows):
        return
    path = model_path(directory)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    options = raw.get("options") if isinstance(raw, dict) else None
    if not isinstance(options, dict):
        return
    rules = []
    for key, description, pattern, invalid in rows:
        rule = {"key": key, "description": description, "pattern": pattern}
        if invalid:
            rule["invalid"] = True
        rules.append(rule)
    options["rules"] = rules
    try:
        _write(path, raw)
    except OSError:
        event("model_save_failed", path=str(path))
        return
    event("invalid_rules_kept", path=str(path), rules=sum(1 for row in rows if row[3]))


def _write(path: Path, document: dict) -> None:
    """The only place the model file is written."""

    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


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


def _options(raw: object) -> ModelOptions | None:
    """Read ``options``. A missing or unusable object leaves the defaults in place."""

    if not isinstance(raw, dict):
        return None
    try:
        rules_raw = raw["rules"]
        if not isinstance(rules_raw, list):
            return None
        rules: list[tuple[str, str, str]] = []
        for item in rules_raw:
            if not isinstance(item, dict):
                return None
            rules.append((str(item["key"]), str(item["description"]), str(item["pattern"])))
        return ModelOptions(
            floor_hours=float(raw["floor_hours"]),
            ceiling_hours=float(raw["ceiling_hours"]),
            min_year=int(raw["min_year"]),
            max_year=int(raw["max_year"]),
            prec_clock=int(raw["prec_clock"]),
            prec_epoch=int(raw["prec_epoch"]),
            prec_date=int(raw["prec_date"]),
            rules=tuple(rules),
        )
    except (KeyError, TypeError, ValueError):
        return None


def _options_document(options: ModelOptions | None) -> dict | None:
    if options is None:
        return None
    return {
        "floor_hours": options.floor_hours,
        "ceiling_hours": options.ceiling_hours,
        "min_year": options.min_year,
        "max_year": options.max_year,
        "prec_clock": options.prec_clock,
        "prec_epoch": options.prec_epoch,
        "prec_date": options.prec_date,
        "rules": [
            {"key": key, "description": description, "pattern": pattern}
            for key, description, pattern in options.rules
        ],
    }


trace_module(sys.modules[__name__])
