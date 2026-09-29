"""Scan a folder, name each event, and move the files.

Other packages import these names from ``filenamecluster.core.operations``.
"""

from .errors import OptionError, OptionFault, OptionField
from .model import keep_rules, load_model, model_path, save_model
from .organize import (
    NamedCluster,
    cluster_name,
    event_folder,
    event_folder_names,
    flatten_cluster_folders,
    is_cluster_folder_name,
    is_folder,
    locate_file,
    move_into_cluster_folders,
)
from .options import OptionReader, rule_error
from .ledger import RuleLedger
from .pipeline import ClusterResult, cluster_directory
from .preview import (
    CurrentPreview,
    FolderPreview,
    FolderScan,
    PreparedPreview,
    SavedOptionsState,
    ScanState,
)

__all__ = [
    "ClusterResult",
    "CurrentPreview",
    "FolderPreview",
    "FolderScan",
    "SavedOptionsState",
    "ScanState",
    "NamedCluster",
    "OptionError",
    "OptionFault",
    "OptionField",
    "OptionReader",
    "PreparedPreview",
    "RuleLedger",
    "cluster_directory",
    "cluster_name",
    "event_folder",
    "event_folder_names",
    "flatten_cluster_folders",
    "is_cluster_folder_name",
    "is_folder",
    "keep_rules",
    "load_model",
    "locate_file",
    "model_path",
    "move_into_cluster_folders",
    "rule_error",
    "save_model",
]
