"""Learn an event boundary from timestamp gaps, and keep that boundary on disk.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
The derivation is ``docs/algorithm.md``.

Nothing here reads image bytes. Each gap is the time between two filenames.
Short gaps and long gaps are treated as two patterns, fitted to this folder
alone, and a pause becomes a new event when it looks more like the long
pattern than the short one.

The fitted boundary is written to ``filenamecluster-model.json`` beside the
files, where it can be opened and inspected. It is not a hidden file. The same
file stores the options last used for that folder under ``options``, beside
``learned``. Options do not change how the boundary is fitted or reused.
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

from filenamecluster.log import detail, event, trace_module

_VARIANCE_FLOOR = 0.05
_SEPARATION = 1.0
# Each pass is one E-step and one M-step, like one training epoch.
# The loop does not stop early when the numbers settle. Change this to refit longer or shorter.
EM_ROUNDS = 25


@dataclass(frozen=True, slots=True)
class GapModel:
    """The short-gap and long-gap patterns learned from one folder."""

    within_hours: float
    between_hours: float
    boundary_hours: float
    separated: bool

    def splits(self, hours: float, floor_hours: float, ceiling_hours: float) -> bool:
        """Whether a pause of ``hours`` should start a new event."""

        if hours <= floor_hours:
            return False
        if hours >= ceiling_hours:
            return True
        return hours >= self.boundary_hours


def fit_gap_model(
    log_hours: list[float],
    forced_within: list[float] | None = None,
    forced_between: list[float] | None = None,
) -> GapModel | None:
    """Fit two log-gap patterns, optionally pinned by corrections.

    ``log_hours`` are unlabeled. ``forced_within`` and ``forced_between`` pin
    log gaps to the short or long pattern. Returns ``None`` when there are too
    few pauses to fit.
    """

    within = list(forced_within or [])
    between = list(forced_between or [])
    unlabeled = list(log_hours)
    samples = len(unlabeled) + len(within) + len(between)
    if samples < 4:
        detail("fit_skipped", samples=samples, need=4)
        return None
    detail("fit_started", unlabeled=len(unlabeled), pinned_within=len(within), pinned_between=len(between))

    ordered = sorted(unlabeled or within + between)
    low = ordered[: max(1, len(ordered) // 2)]
    high = ordered[max(1, len(ordered) // 2) :]
    mean_within = _mean(low)
    mean_between = _mean(high)
    var_within = max(_variance(low, mean_within), _VARIANCE_FLOOR)
    var_between = max(_variance(high, mean_between), _VARIANCE_FLOOR)
    weight_within = 0.5

    for step in range(EM_ROUNDS):
        responsibilities: list[tuple[float, float, float]] = []
        for value in unlabeled:
            within_share = _responsibility(
                value,
                mean_within,
                var_within,
                weight_within,
                mean_between,
                var_between,
            )
            responsibilities.append((value, within_share, 1.0 - within_share))
        for value in within:
            responsibilities.append((value, 1.0, 0.0))
        for value in between:
            responsibilities.append((value, 0.0, 1.0))

        total_within = sum(share for _, share, _ in responsibilities)
        total_between = sum(share for _, _, share in responsibilities)
        total = total_within + total_between
        if total_within < 1e-6 or total_between < 1e-6:
            detail("fit_collapsed", step=step, weight_within=total_within, weight_between=total_between)
            break
        mean_within = sum(value * share for value, share, _ in responsibilities) / total_within
        mean_between = sum(value * share for value, _, share in responsibilities) / total_between
        var_within = max(
            sum(share * (value - mean_within) ** 2 for value, share, _ in responsibilities)
            / total_within,
            _VARIANCE_FLOOR,
        )
        var_between = max(
            sum(share * (value - mean_between) ** 2 for value, _, share in responsibilities)
            / total_between,
            _VARIANCE_FLOOR,
        )
        weight_within = total_within / total
        swapped = mean_within > mean_between
        if swapped:
            mean_within, mean_between = mean_between, mean_within
            var_within, var_between = var_between, var_within
            weight_within = 1.0 - weight_within
        detail(
            "fit_iteration",
            step=step,
            within_hours=math.exp(mean_within),
            between_hours=math.exp(mean_between),
            weight_within=weight_within,
            swapped=swapped,
        )

    separated = mean_between - mean_within >= _SEPARATION and 0.05 < weight_within < 0.95
    if separated:
        boundary = _boundary(
            mean_within,
            var_within,
            weight_within,
            mean_between,
            var_between,
            1.0 - weight_within,
        )
    else:
        logs = unlabeled + within + between
        center = _mean(logs)
        spread = math.sqrt(max(_variance(logs, center), _VARIANCE_FLOOR))
        # A single short rhythm is one occasion, so only an unusual pause
        # splits it. A single rhythm of a day or more is a repeated occasion,
        # so a typical pause of that size starts a new event.
        if center >= math.log(18):
            boundary = center - 0.5 * spread
        else:
            boundary = center + 2.0 * spread
    model = GapModel(
        within_hours=math.exp(mean_within),
        between_hours=math.exp(mean_between),
        boundary_hours=math.exp(boundary),
        separated=separated,
    )
    detail(
        "fit_finished",
        within_hours=model.within_hours,
        between_hours=model.between_hours,
        boundary_hours=model.boundary_hours,
        separated=model.separated,
        rule="two_hills" if separated else "one_rhythm",
    )
    return model


def _responsibility(
    value: float,
    mean_within: float,
    var_within: float,
    weight_within: float,
    mean_between: float,
    var_between: float,
) -> float:
    log_within = _log_density(value, mean_within, var_within) + math.log(max(weight_within, 1e-6))
    log_between = _log_density(value, mean_between, var_between) + math.log(
        max(1.0 - weight_within, 1e-6)
    )
    if log_within >= log_between:
        return 1.0 / (1.0 + math.exp(log_between - log_within))
    return math.exp(log_within - log_between) / (1.0 + math.exp(log_within - log_between))


def _log_density(value: float, mean: float, variance: float) -> float:
    return -0.5 * (math.log(2.0 * math.pi * variance) + (value - mean) ** 2 / variance)


def _boundary(
    mean_within: float,
    var_within: float,
    weight_within: float,
    mean_between: float,
    var_between: float,
    weight_between: float,
) -> float:
    """Log-gap where the two patterns are equally likely, between their centers."""

    a = 1.0 / var_within - 1.0 / var_between
    b = -2.0 * mean_within / var_within + 2.0 * mean_between / var_between
    c = (
        mean_within**2 / var_within
        - mean_between**2 / var_between
        + math.log(var_within / var_between)
        - 2.0 * math.log(max(weight_within, 1e-6) / max(weight_between, 1e-6))
    )
    if abs(a) < 1e-9:
        root = -c / b if abs(b) > 1e-9 else (mean_within + mean_between) / 2.0
        roots = [root]
    else:
        discriminant = b**2 - 4.0 * a * c
        if discriminant < 0:
            roots = []
        else:
            span = math.sqrt(discriminant)
            roots = [(-b - span) / (2.0 * a), (-b + span) / (2.0 * a)]
    inside = [root for root in roots if mean_within < root < mean_between]
    if inside:
        return inside[0]
    return (mean_within + mean_between) / 2.0


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _variance(values: list[float], center: float) -> float:
    if len(values) < 2:
        return _VARIANCE_FLOOR
    return sum((value - center) ** 2 for value in values) / len(values)


MODEL_NAME = "filenamecluster-model.json"


@dataclass(frozen=True, slots=True)
class ModelOptions:
    """Safety limits, year window, priorities, and filename rules for one folder.

    Saved beside ``learned``. Loading them overrides the built-in defaults.
    Fitting and reusing the boundary does not read this object.
    """

    floor_hours: float
    ceiling_hours: float
    min_year: int
    max_year: int
    prec_clock: int
    prec_epoch: int
    prec_date: int
    rules: tuple[tuple[str, str, str], ...]


@dataclass(frozen=True, slots=True)
class FolderModel:
    """The boundary and options last written for one folder."""

    learned: GapModel | None = None
    options: ModelOptions | None = None

    def with_learned(self, learned: GapModel | None) -> FolderModel:
        """Replace the boundary and keep the saved options."""

        return FolderModel(learned, self.options)

    def with_options(self, options: ModelOptions | None) -> FolderModel:
        """Replace the saved options and keep the boundary."""

        return FolderModel(self.learned, options)


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
    document = {
        "learned": _learned_document(model.learned),
        "options": _options_document(model.options),
    }
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    event("model_saved", path=str(path), learned=model.learned is not None, options=model.options is not None)
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
