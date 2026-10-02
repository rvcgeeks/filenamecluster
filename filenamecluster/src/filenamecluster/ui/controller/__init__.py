"""Clicks, preview, apply, and flatten.

Other packages import these names from ``filenamecluster.ui.controller``.
They do not import the modules inside this package directly.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from .controller import AppController
from .files import SystemFiles
from .logging import SystemLogging
from .ports import (
    ActionsPort,
    DialogPort,
    DiskPort,
    FolderPickerPort,
    LoggingPort,
    TaskRunnerPort,
    ViewPort,
)
from .requests import (
    Applied,
    ApplyCreate,
    ApplyUpdate,
    CouldNotFlatten,
    CouldNotMove,
    Failure,
    FileMissing,
    FlattenAsk,
    Flattened,
    FolderMissing,
    NothingToFlatten,
    NothingToMove,
    Notice,
    PatternBlank,
    PatternInvalid,
    PatternValid,
    RenameRejected,
    Question,
    Success,
    Wait,
)

__all__ = [
    "ActionsPort",
    "AppController",
    "Applied",
    "ApplyCreate",
    "ApplyUpdate",
    "CouldNotFlatten",
    "CouldNotMove",
    "DialogPort",
    "DiskPort",
    "Failure",
    "FileMissing",
    "FlattenAsk",
    "Flattened",
    "FolderMissing",
    "FolderPickerPort",
    "LoggingPort",
    "NothingToFlatten",
    "NothingToMove",
    "Notice",
    "PatternBlank",
    "PatternInvalid",
    "PatternValid",
    "Question",
    "RenameRejected",
    "Success",
    "SystemFiles",
    "SystemLogging",
    "TaskRunnerPort",
    "ViewPort",
    "Wait",
]
