"""The status line and the dialogs, in the current language.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import sys
from pathlib import Path

from filenamecluster.core import OptionFault, OptionField
from filenamecluster.log import trace_module
from filenamecluster.ui.controller import (
    Applied,
    ApplyCreate,
    ApplyUpdate,
    CouldNotFlatten,
    CouldNotMove,
    FileMissing,
    FlattenAsk,
    Flattened,
    FolderMissing,
    NothingToFlatten,
    RenameRejected,
    StorageRequired,
    NothingToMove,
    PatternBlank,
    PatternInvalid,
    PatternValid,
    Wait,
)
from filenamecluster.ui.model import (
    NameClash,
    ChooseStatus,
    OptionProblemStatus,
    PreviewStaysStatus,
    ReadFailureStatus,
    SummaryStatus,
    ValueProblemStatus,
)
from .i18n import describe_model

_FAULTS = {
    OptionFault.NOT_A_NUMBER: "must_be_number",
    OptionFault.NOT_WHOLE: "must_be_whole",
    OptionFault.OUT_OF_RANGE: "must_be_between",
}
_FIELDS = {
    OptionField.FLOOR: "floor_label",
    OptionField.CEILING: "ceiling_label",
    OptionField.MIN_YEAR: "limit_min_year",
    OptionField.MAX_YEAR: "limit_max_year",
    OptionField.PREC_CLOCK: "limit_prec_clock",
    OptionField.PREC_EPOCH: "limit_prec_epoch",
    OptionField.PREC_DATE: "limit_prec_date",
}

_WAITS = {
    Wait.OPEN: "busy_open",
    Wait.PREVIEW: "busy_preview",
    Wait.APPLY_CHECK: "busy_apply_check",
    Wait.APPLY: "busy_apply",
    Wait.NAME_CHECK: "busy_name_check",
    Wait.FLATTEN_CHECK: "busy_flatten_check",
    Wait.FLATTEN: "busy_flatten",
    Wait.AFTER_FLATTEN: "busy_after_flatten",
    Wait.AFTER_ERROR: "busy_after_error",
}


class Messages:
    """Turn semantic requests and status values into catalog sentences."""

    def __init__(self, host) -> None:
        self.host = host

    def present(self, notice) -> None:
        """Show the dialog for one notice, using the current catalog."""

        if isinstance(notice, PatternBlank):
            self.tell_info("pattern_valid_title", "pattern_blank_body")
        elif isinstance(notice, PatternValid):
            description = notice.description.strip() or self.host.translate("custom_pattern")
            self.tell_info("pattern_valid_title", "pattern_valid_body", description=description)
        elif isinstance(notice, PatternInvalid):
            self.tell_error("pattern_invalid_title", notice.detail)
        elif isinstance(notice, NothingToMove):
            self.tell_info("nothing_to_move_title", "nothing_to_move_body")
        elif isinstance(notice, Applied):
            if notice.skipped:
                self.tell_info(
                    "applied_title",
                    "applied_body_skipped",
                    files=notice.files,
                    events=notice.events,
                    skipped=notice.skipped,
                )
            else:
                self.tell_info(
                    "applied_title", "applied_body", files=notice.files, events=notice.events
                )
        elif isinstance(notice, CouldNotMove):
            self.tell_error("could_not_move", notice.detail)
        elif isinstance(notice, NothingToFlatten):
            self.tell_info("nothing_to_flatten_title", "nothing_to_flatten_body")
        elif isinstance(notice, Flattened):
            self.tell_info(
                "flattened_title", "flattened_body", moved=notice.moved, name=notice.name
            )
        elif isinstance(notice, CouldNotFlatten):
            self.tell_error("could_not_flatten", notice.detail)
        elif isinstance(notice, FileMissing):
            self.tell_warning("file_missing_title", "file_missing_body", name=notice.name)
        elif isinstance(notice, FolderMissing):
            self.tell_warning("folder_missing_title", "folder_missing_body", name=notice.name)
        elif isinstance(notice, StorageRequired):
            self.tell_info("storage_required_title", "storage_required_body")
        elif isinstance(notice, RenameRejected):
            self._rename_rejected(notice)
        else:
            raise TypeError(f"unknown notice {type(notice).__name__}")

    def _rename_rejected(self, notice: RenameRejected) -> None:
        if notice.reason == "exists":
            body = self.host.translate("rename_exists_body", name=notice.name)
            self.tell_error("rename_exists_title", body)
            return
        if notice.reason == "failed":
            body = self.host.translate("rename_failed_body", detail=notice.detail)
            self.tell_error("rename_failed_title", body)
            return
        self.tell_error("rename_invalid_title", self.host.translate("rename_invalid_body"))

    def question(self, asked) -> bool:
        if isinstance(asked, ApplyCreate):
            return self.ask(
                "apply", "apply_create", path=asked.path, files=asked.files, events=asked.events
            )
        if isinstance(asked, ApplyUpdate):
            return self.ask(
                "apply", "apply_update", path=asked.path, files=asked.files, events=asked.events
            )
        if isinstance(asked, FlattenAsk):
            body = "flatten_confirm_notes" if asked.noted else "flatten_confirm"
            return self.ask(
                "flatten", body, folders=asked.folders, path=asked.path, noted=asked.noted
            )
        raise TypeError(f"unknown question {type(asked).__name__}")

    def wait_key(self, wait: Wait) -> str:
        return _WAITS[wait]

    def choose_directory(self, initial: Path, title_key: str = "choose_title") -> str:
        return self.host.dialogs.choose_directory(initial, title_key)

    def resolve_clash(self, clash: NameClash) -> None:
        """Translate one destination-name clash and let the dialog write the choice."""

        everyone = self.host.translate("clash_all", count=clash.count) if clash.count > 1 else None
        self.host.dialogs.ask_name_clash(
            clash,
            title=self.host.translate("clash_title"),
            body=self.host.translate("clash_body", name=clash.name),
            replace=self.host.translate("clash_replace"),
            skip=self.host.translate("clash_skip"),
            everyone=everyone,
        )

    def ask(self, title_key: str, body_key: str, **fields: object) -> bool:
        return self.host.dialogs.ask_yes_no(
            self.host.translate(title_key),
            self.host.translate(body_key, **fields),
        )

    def tell_info(self, title_key: str, body_key: str, **fields: object) -> None:
        self.host.dialogs.info(
            self.host.translate(title_key),
            self.host.translate(body_key, **fields),
        )

    def tell_error(self, title_key: str, body: str) -> None:
        self.host.dialogs.error(self.host.translate(title_key), body)

    def tell_warning(self, title_key: str, body_key: str, **fields: object) -> None:
        self.host.dialogs.warning(
            self.host.translate(title_key),
            self.host.translate(body_key, **fields),
        )

    def paint_status(self, status) -> None:
        """Translate and draw one status variant."""

        if isinstance(status, SummaryStatus):
            text = self._summary(status)
        elif isinstance(status, OptionProblemStatus):
            values = {"label": self.host.translate(_FIELDS[status.field])}
            if status.low is not None:
                values["low"] = status.low
                values["high"] = status.high
            text = self.host.translate(
                "options_error",
                message=self.host.translate(_FAULTS[status.fault], **values),
            )
        elif isinstance(status, ValueProblemStatus):
            text = self.host.translate("options_error", message=status.message)
        elif isinstance(status, ReadFailureStatus):
            text = self.host.translate(
                "could_not_read", path=status.path, error=status.error
            )
        elif isinstance(status, PreviewStaysStatus):
            text = self.host.translate(
                "preview_stays", files=status.files, events=status.events
            )
        elif isinstance(status, ChooseStatus):
            text = self.host.translate("choose_status")
        else:
            raise TypeError(f"unknown status {type(status).__name__}")
        self._set_status(text, status.failed)

    def _set_status(self, message: str, error: bool = False) -> None:
        self.host.status_text.set(message)
        self.host.status.configure(style="Error.TLabel" if error else "Status.TLabel")

    def _summary(self, status: SummaryStatus) -> str:
        included = (
            self.host.translate("event_folders_included", n=status.event_folders)
            if status.event_folders
            else ""
        )
        text = self.host.translate(
            "status_summary",
            events=status.events,
            files=status.files,
            missing=status.missing,
            included=included,
            folders=status.other_folders,
            model=describe_model(status.learned, translate=self.host.translate),
        )
        if status.left_out:
            text = f"{text} {self.host.translate('patterns_left_out', n=status.left_out)}"
        return text


trace_module(sys.modules[__name__])
