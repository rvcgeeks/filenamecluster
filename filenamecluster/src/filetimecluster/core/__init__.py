"""Read filename timestamps, cluster files into events, and move them into folders.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Introduction: ``readme.md``. Mathematics: ``docs/algorithm.md``.
Design: ``docs/architecture.md``.
"""

from filetimecluster.core.cluster import Cluster, ClusterParams, cluster_files
from filetimecluster.core.organize import (
    NamedCluster,
    cluster_name,
    flatten_cluster_folders,
    is_cluster_folder_name,
    move_into_cluster_folders,
)
from filetimecluster.core.parse import (
    TimestampPatterns,
    TimestampedFile,
    parse_timestamp,
    scan_directory,
)
from filetimecluster.core.pipeline import ClusterResult, cluster_directory

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
