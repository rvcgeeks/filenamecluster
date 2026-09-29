"""Scan a folder, read each file's capture time, and cluster the files.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``. Mathematics: ``docs/algorithm.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
import sys
from datetime import datetime, timedelta
from pathlib import Path

from filenamecluster.core.algorithm.cluster import ClusterParams, ModelOptions, cluster
from filenamecluster.core.algorithm.fit import GapModel
from filenamecluster.core.exif import read_exif_timestamp
from .model import load_model, save_model
from .organize import NamedCluster, name_clusters
from filenamecluster.core.parser import (
    CompiledTimestampPatterns,
    PatternRule,
    TimestampPatterns,
    TimestampedFile,
    parse_timestamp,
    scan_directory,
)
from filenamecluster.log import detail, event, log_call, trace_module


@dataclass(frozen=True, slots=True)
class ClusterResult:
    """Clusters in chronological order, plus everything that was skipped."""

    clusters: tuple[NamedCluster, ...]
    ignored_without_timestamp: tuple[str, ...]
    ignored_directories: tuple[str, ...]
    params: ClusterParams
    model: GapModel | None = None

    @property
    def file_count(self) -> int:
        return sum(len(cluster.files) for cluster in self.clusters)


def _capture_time(path: Path, name: str, compiled: CompiledTimestampPatterns) -> datetime | None:
    """Filename clock first. Otherwise the picture, video, or PDF capture time.

    ``None`` means there is no usable clock. The caller lists that file as
    skipped, including when the capture time cannot be read.
    """

    stamp = parse_timestamp(name, compiled)
    if stamp is not None:
        return stamp
    try:
        return read_exif_timestamp(path, compiled.min_year, compiled.max_year)
    except Exception:  # noqa: BLE001  # an unreadable capture time is skipped
        return None


def cluster_directory(
    directory: Path | str,
    params: ClusterParams | None = None,
    patterns: TimestampPatterns | None = None,
) -> ClusterResult:
    """Cluster the files in ``directory`` by capture time.

    The time is read from the filename. When the name has none, a picture's
    EXIF capture time, a video container clock, or PDF CreationDate is used.
    Other files are not opened for a clock. A file whose capture time cannot
    be read is listed as skipped. Filesystem dates are not used.
    """

    folder = Path(directory)
    event("cluster_started", path=str(folder))
    log_call("filenamecluster.core.operations.model.load_model")
    corrections = load_model(folder)
    chosen = params if params is not None else _params_from_options(corrections.options)
    pattern_source = patterns if patterns is not None else _patterns_from_options(corrections.options)
    detail(
        "limits_chosen",
        source="caller" if params is not None else "saved" if corrections.options is not None else "defaults",
        floor_hours=chosen.floor_hours,
        ceiling_hours=chosen.ceiling_hours,
    )
    detail(
        "patterns_chosen",
        source="caller" if patterns is not None else "saved" if corrections.options is not None else "defaults",
        rules=len(pattern_source.rules),
        enabled=sum(1 for rule in pattern_source.rules if rule.pattern.strip()),
        min_year=pattern_source.min_year,
        max_year=pattern_source.max_year,
        prec_clock=pattern_source.prec_clock,
        prec_epoch=pattern_source.prec_epoch,
        prec_date=pattern_source.prec_date,
    )
    compiled = pattern_source.compile()
    log_call("filenamecluster.core.parser.scan_directory")
    contents = scan_directory(folder)
    stamped: list[TimestampedFile] = []
    ignored: list[str] = []
    for name in contents.files:
        stamp = _capture_time(folder / name, name, compiled)
        if stamp is None:
            # No filename clock, and the capture time could not be read.
            ignored.append(name)
            detail("capture_missing", name=name)
        else:
            stamped.append(TimestampedFile(name, stamp))
            detail("capture_read", name=name, stamp=stamp.isoformat(sep=" "), source="loose")
    for dirname, name in contents.placed:
        stamp = _capture_time(folder / dirname / name, name, compiled)
        placed_name = f"{dirname}/{name}"
        if stamp is None:
            ignored.append(placed_name)
            detail("capture_missing", name=placed_name)
        else:
            stamped.append(TimestampedFile(name, stamp, source=placed_name))
            detail("capture_read", name=placed_name, stamp=stamp.isoformat(sep=" "), source="event_folder")
    log_call("filenamecluster.core.algorithm.cluster.cluster")
    clusters, learned = cluster(stamped, chosen, corrections)
    try:
        log_call("filenamecluster.core.operations.model.save_model")
        save_model(
            folder,
            corrections.with_learned(learned).with_options(_options_from(chosen, pattern_source)),
        )
    except OSError:
        event("model_save_failed", path=str(folder))
    result = ClusterResult(
        clusters=tuple(name_clusters(clusters)),
        ignored_without_timestamp=tuple(ignored),
        ignored_directories=contents.directories,
        params=chosen,
        model=learned,
    )
    event("cluster_finished", path=str(folder), events=len(result.clusters), files=result.file_count)
    return result


def _params_from_options(options: ModelOptions | None) -> ClusterParams:
    """Saved safety limits override the built-in defaults. Invalid values do not."""

    if options is None:
        detail("saved_limits_absent")
        return ClusterParams()
    try:
        return ClusterParams(
            floor=timedelta(hours=options.floor_hours),
            ceiling=timedelta(hours=options.ceiling_hours),
        )
    except (TypeError, ValueError, OverflowError):
        detail("saved_limits_rejected", floor_hours=options.floor_hours, ceiling_hours=options.ceiling_hours)
        return ClusterParams()


def _patterns_from_options(options: ModelOptions | None) -> TimestampPatterns:
    """Saved filename rules override the built-in defaults. Invalid rules do not."""

    if options is None:
        detail("saved_patterns_absent")
        return TimestampPatterns()
    try:
        chosen = TimestampPatterns(
            rules=tuple(
                PatternRule(key, description, pattern) for key, description, pattern in options.rules
            ),
            min_year=options.min_year,
            max_year=options.max_year,
            prec_clock=options.prec_clock,
            prec_epoch=options.prec_epoch,
            prec_date=options.prec_date,
        )
        chosen.compile()
    except (TypeError, ValueError, OverflowError) as exc:
        detail("saved_patterns_rejected", error=type(exc).__name__)
        return TimestampPatterns()
    return chosen


def _options_from(params: ClusterParams, patterns: TimestampPatterns) -> ModelOptions:
    """The options actually used for this scan, ready to store beside ``learned``."""

    return ModelOptions(
        floor_hours=params.floor_hours,
        ceiling_hours=params.ceiling_hours,
        min_year=patterns.min_year,
        max_year=patterns.max_year,
        prec_clock=patterns.prec_clock,
        prec_epoch=patterns.prec_epoch,
        prec_date=patterns.prec_date,
        rules=tuple((rule.key, rule.description, rule.pattern) for rule in patterns.rules),
    )


trace_module(sys.modules[__name__])
