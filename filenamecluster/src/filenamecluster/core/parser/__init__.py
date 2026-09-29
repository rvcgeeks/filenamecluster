"""Filename patterns and the folder listing that uses them.

Other packages import these names from ``filenamecluster.core.parser``.
"""

from .patterns import CompiledTimestampPatterns, LIMIT_FIELDS, PatternRule, TimestampPatterns
from .scan import (
    MODEL_NAME,
    FolderContents,
    TimestampedFile,
    is_cluster_folder_name,
    parse_timestamp,
    scan_directory,
)

__all__ = [
    "MODEL_NAME",
    "LIMIT_FIELDS",
    "CompiledTimestampPatterns",
    "FolderContents",
    "PatternRule",
    "TimestampPatterns",
    "TimestampedFile",
    "is_cluster_folder_name",
    "parse_timestamp",
    "scan_directory",
]
