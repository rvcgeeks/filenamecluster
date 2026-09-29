"""Read filename timestamps, cluster files into events, and move them into folders.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Introduction: ``readme.md``. Mathematics: ``docs/algorithm.md``.
Design: ``docs/architecture.md``.
"""

import sys
from filenamecluster.log import trace_module

from filenamecluster.core.algorithm.cluster import Cluster, ClusterParams, cluster
from filenamecluster.core.operations.organize import (
    NamedCluster,
    cluster_name,
    flatten_cluster_folders,
    is_cluster_folder_name,
    move_into_cluster_folders,
)
from filenamecluster.core.parser import (
    TimestampPatterns,
    TimestampedFile,
    parse_timestamp,
    scan_directory,
)
from filenamecluster.core.operations.pipeline import ClusterResult, cluster_directory

__all__ = [
    "Cluster",
    "ClusterParams",
    "ClusterResult",
    "NamedCluster",
    "TimestampPatterns",
    "TimestampedFile",
    "cluster_directory",
    "cluster",
    "cluster_name",
    "flatten_cluster_folders",
    "is_cluster_folder_name",
    "move_into_cluster_folders",
    "parse_timestamp",
    "scan_directory",
]

trace_module(sys.modules[__name__])
