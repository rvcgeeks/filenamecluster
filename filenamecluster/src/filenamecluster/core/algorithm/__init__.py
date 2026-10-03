"""The event boundary: order the gaps, fit two patterns, and split on the boundary.

``filenamecluster.core`` re-exports these names. Other packages import them
from there. The derivation is ``docs/algorithm.md``.
"""

from .cluster import Cluster, ClusterParams, FolderModel, ModelOptions, cluster
from .fit import EM_ROUNDS, GapModel, _VARIANCE_FLOOR, _boundary, _variance, fit
from .split import FALLBACK_HOURS, split

__all__ = [
    "EM_ROUNDS",
    "FALLBACK_HOURS",
    "_VARIANCE_FLOOR",
    "_boundary",
    "_variance",
    "Cluster",
    "ClusterParams",
    "FolderModel",
    "GapModel",
    "ModelOptions",
    "cluster",
    "fit",
    "split",
]
