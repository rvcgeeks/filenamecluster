"""Scan a folder, read each file's capture time, and cluster the files.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``. Mathematics: ``docs/algorithm.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from filenamecluster.core.cluster import ClusterParams, cluster_files
from filenamecluster.core.exif import read_exif_timestamp
from filenamecluster.core.learn import GapModel, load_model, save_model
from filenamecluster.core.organize import NamedCluster, name_clusters
from filenamecluster.core.parse import (
    CompiledTimestampPatterns,
    TimestampPatterns,
    TimestampedFile,
    parse_timestamp,
    scan_directory,
)


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
    except Exception:
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
    chosen = params or ClusterParams()
    compiled = (patterns or TimestampPatterns()).compile()
    corrections = load_model(folder)
    contents = scan_directory(folder)
    stamped: list[TimestampedFile] = []
    ignored: list[str] = []
    for name in contents.files:
        stamp = _capture_time(folder / name, name, compiled)
        if stamp is None:
            # No filename clock, and the capture time could not be read.
            ignored.append(name)
        else:
            stamped.append(TimestampedFile(name, stamp))
    for dirname, name in contents.placed:
        stamp = _capture_time(folder / dirname / name, name, compiled)
        if stamp is None:
            ignored.append(f"{dirname}/{name}")
        else:
            stamped.append(TimestampedFile(name, stamp, source=f"{dirname}/{name}"))
    clusters, learned = cluster_files(stamped, chosen, corrections)
    try:
        save_model(folder, corrections.with_learned(learned))
    except OSError:
        pass
    return ClusterResult(
        clusters=tuple(name_clusters(clusters)),
        ignored_without_timestamp=tuple(ignored),
        ignored_directories=contents.directories,
        params=chosen,
        model=learned,
    )
