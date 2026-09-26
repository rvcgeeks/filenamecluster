"""Scan a folder, read each filename's timestamp, and cluster the files.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``. Mathematics: ``docs/algorithm.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from filenamecluster.core.cluster import ClusterParams, cluster_files
from filenamecluster.core.learn import GapModel
from filenamecluster.core.model_file import load_model, save_model
from filenamecluster.core.organize import NamedCluster, name_clusters
from filenamecluster.core.parse import (
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


def cluster_directory(
    directory: Path | str,
    params: ClusterParams | None = None,
    patterns: TimestampPatterns | None = None,
) -> ClusterResult:
    """Cluster the files sitting directly in ``directory`` by filename time."""

    folder = Path(directory)
    chosen = params or ClusterParams()
    compiled = (patterns or TimestampPatterns()).compile()
    corrections = load_model(folder)
    contents = scan_directory(folder)
    stamped: list[TimestampedFile] = []
    ignored: list[str] = []
    for name in contents.files:
        stamp = parse_timestamp(name, compiled)
        if stamp is None:
            ignored.append(name)
        else:
            stamped.append(TimestampedFile(name, stamp))
    for dirname, name in contents.placed:
        stamp = parse_timestamp(name, compiled)
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
