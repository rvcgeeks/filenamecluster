"""Learn an event boundary from timestamp gaps, and keep that boundary on disk.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
The derivation is ``docs/algorithm.md``.

Nothing here reads image bytes. Each gap is the time between two filenames.
Short gaps and long gaps are treated as two patterns, fitted to this folder
alone, and a pause becomes a new event when it looks more like the long
pattern than the short one.

The fitted boundary is written to ``filenamecluster-model.json`` beside the
files, where it can be opened and inspected. It is not a hidden file.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

_VARIANCE_FLOOR = 0.05
_SEPARATION = 1.0


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
    if len(unlabeled) + len(within) + len(between) < 4:
        return None

    ordered = sorted(unlabeled or within + between)
    low = ordered[: max(1, len(ordered) // 2)]
    high = ordered[max(1, len(ordered) // 2) :]
    mean_within = _mean(low)
    mean_between = _mean(high)
    var_within = max(_variance(low, mean_within), _VARIANCE_FLOOR)
    var_between = max(_variance(high, mean_between), _VARIANCE_FLOOR)
    weight_within = 0.5

    for _ in range(25):
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
        if mean_within > mean_between:
            mean_within, mean_between = mean_between, mean_within
            var_within, var_between = var_between, var_within
            weight_within = 1.0 - weight_within

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
    return GapModel(
        within_hours=math.exp(mean_within),
        between_hours=math.exp(mean_between),
        boundary_hours=math.exp(boundary),
        separated=separated,
    )


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
class FolderModel:
    """The boundary last written for one folder."""

    learned: GapModel | None = None

    def with_learned(self, learned: GapModel | None) -> FolderModel:
        return FolderModel(learned)


def model_path(directory: Path | str) -> Path:
    return Path(directory) / MODEL_NAME


def load_model(directory: Path | str) -> FolderModel:
    """Load ``filenamecluster-model.json``, or an empty model when it is absent."""

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
