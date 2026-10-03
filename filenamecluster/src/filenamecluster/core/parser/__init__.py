"""Filename patterns and the folder listing that uses them.

``filenamecluster.core`` re-exports these names. Other packages import them
from there.
"""

from .folders import event_folder_parts, name_with_note
from .patterns import (
    DEFAULT_RULES,
    LIMIT_FIELDS,
    CompiledTimestampPatterns,
    PatternRule,
    TimestampPatterns,
)
from .scan import (
    MODEL_NAME,
    FolderContents,
    TimestampedFile,
    is_cluster_folder_name,
    _from_epoch_millis,
    parse_timestamp,
    scan_directory,
)

__all__ = [
    "DEFAULT_RULES",
    "_from_epoch_millis",
    "MODEL_NAME",
    "LIMIT_FIELDS",
    "CompiledTimestampPatterns",
    "FolderContents",
    "PatternRule",
    "TimestampPatterns",
    "TimestampedFile",
    "event_folder_parts",
    "is_cluster_folder_name",
    "name_with_note",
    "parse_timestamp",
    "scan_directory",
]
