"""The event boundary: order the gaps, fit two patterns, and split on the boundary.

Other packages import these names from ``filenamecluster.core.algorithm``.
The derivation is ``docs/algorithm.md``.
"""

from .cluster import Cluster, ClusterParams, FolderModel, ModelOptions, cluster
from .fit import EM_ROUNDS, GapModel, fit
from .split import FALLBACK_HOURS, split

__all__ = [
    "EM_ROUNDS",
    "FALLBACK_HOURS",
    "Cluster",
    "ClusterParams",
    "FolderModel",
    "GapModel",
    "ModelOptions",
    "cluster",
    "fit",
    "split",
]
