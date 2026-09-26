"""Read filename timestamps, cluster files into events, and move them into folders.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Introduction: ``readme.md``. Mathematics: ``docs/algorithm.md``.
Design: ``docs/architecture.md``.
"""

from filenamecluster.core.cluster import Cluster, ClusterParams, cluster_files
from filenamecluster.core.organize import (
    NamedCluster,
    cluster_name,
    flatten_cluster_folders,
    is_cluster_folder_name,
    move_into_cluster_folders,
)
from filenamecluster.core.parse import (
    TimestampPatterns,
    TimestampedFile,
    parse_timestamp,
    scan_directory,
)
from filenamecluster.core.pipeline import ClusterResult, cluster_directory

__all__ = [
    "Cluster",
    "ClusterParams",
    "ClusterResult",
    "NamedCluster",
    "TimestampPatterns",
    "TimestampedFile",
    "cluster_directory",
    "cluster_files",
    "cluster_name",
    "flatten_cluster_folders",
    "is_cluster_folder_name",
    "move_into_cluster_folders",
    "parse_timestamp",
    "scan_directory",
]
