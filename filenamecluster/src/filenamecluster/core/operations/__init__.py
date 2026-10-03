"""Scan a folder, name each event, and move the files.

``filenamecluster.core`` re-exports these names. Other packages import them
from there.
"""

from .errors import OptionError, OptionFault, OptionField
from .model import (
    keep_folder_notes,
    keep_rules,
    load_folder_notes,
    load_model,
    model_path,
    save_model,
    store_if_changed,
)
from .notes import noted_name
from .organize import (
    NamedCluster,
    cluster_name,
    event_folder,
    event_folder_names,
    find_event_folder,
    flatten_cluster_folders,
    folder_note,
    is_cluster_folder_name,
    is_folder,
    locate_file,
    move_into_cluster_folders,
    name_clusters,
    plan_cluster_moves,
    plan_flatten_moves,
)
from .options import OptionReader, rule_error
from .ledger import RuleLedger
from .pipeline import (
    ClusterResult,
    _params_from_options,
    _patterns_from_options,
    cluster_directory,
    option_signature,
)
from .placement import PlannedMove, _overwrite, commit_cluster_moves, survey_flatten
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
    "_overwrite",
    "_params_from_options",
    "_patterns_from_options",
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
    "PlannedMove",
    "PreparedPreview",
    "RuleLedger",
    "cluster_directory",
    "cluster_name",
    "commit_cluster_moves",
    "event_folder",
    "event_folder_names",
    "find_event_folder",
    "flatten_cluster_folders",
    "folder_note",
    "is_cluster_folder_name",
    "is_folder",
    "keep_folder_notes",
    "keep_rules",
    "load_folder_notes",
    "load_model",
    "store_if_changed",
    "locate_file",
    "model_path",
    "move_into_cluster_folders",
    "name_clusters",
    "noted_name",
    "plan_cluster_moves",
    "plan_flatten_moves",
    "rule_error",
    "save_model",
    "option_signature",
    "survey_flatten",
]
