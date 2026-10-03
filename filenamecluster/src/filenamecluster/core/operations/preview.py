"""Scan a folder with its saved options.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import timedelta
from enum import Enum, auto
from pathlib import Path

from filenamecluster.core.algorithm.cluster import ClusterParams
from filenamecluster.core.algorithm import ModelOptions
from filenamecluster.core.parser import PatternRule, TimestampPatterns
from filenamecluster.log import detail, log_call, trace_module
from .ledger import RuleLedger
from .model import load_model
from .options import OptionReader, rule_error
from .pipeline import ClusterResult, cluster_directory


@dataclass(frozen=True, slots=True)
class CurrentPreview:
    """A fresh preview and the ids of rules left out of it."""

    result: ClusterResult
    invalid: frozenset[str]


class ScanState(Enum):
    """Whether the folder could be read."""

    OK = auto()
    READ_ERROR = auto()


class SavedOptionsState(Enum):
    """How saved options were treated before the scan."""

    LOADED = auto()
    IGNORED = auto()
    DEFAULTS = auto()


@dataclass(frozen=True, slots=True)
class FolderScan:
    """The typed result of opening one folder."""

    state: ScanState
    saved: SavedOptionsState
    options: ModelOptions | None
    result: ClusterResult | None = None
    error: OSError | None = None


@dataclass(frozen=True, slots=True)
class PreparedPreview:
    """Compiled current drafts, ready for disk work."""

    params: ClusterParams
    patterns: TimestampPatterns
    invalid: frozenset[str]
    table: tuple[tuple[str, str, str, str, bool], ...]


class FolderPreview:
    """Load ``filenamecluster-model.json`` and cluster the folder."""

    def scan(self, directory: Path, source: Path | None = None) -> FolderScan:
        """Scan one folder and report how its saved options were treated."""

        loaded = load_model(directory)
        options = loaded.options
        accepted = self._compiled(options) if options is not None else None
        if options is not None and accepted is None:
            saved = SavedOptionsState.IGNORED
        elif accepted is not None:
            saved = SavedOptionsState.LOADED
        else:
            saved = SavedOptionsState.DEFAULTS
        if accepted is None:
            params, patterns = ClusterParams(), TimestampPatterns()
        else:
            params, patterns = accepted
        try:
            log_call("filenamecluster.core.operations.pipeline.cluster_directory")
            result = cluster_directory(directory, params, patterns, source=source, loaded=loaded)
        except OSError as exc:
            return FolderScan(ScanState.READ_ERROR, saved, options, error=exc)
        if accepted is not None:
            RuleLedger.mark(directory, self.marked(options))
        return FolderScan(ScanState.OK, saved, options, result=result)

    def prepare(
        self,
        option_text: dict[str, str],
        limit_text: dict[str, str],
        table: list[tuple[str, str, str, str, bool]],
    ) -> PreparedPreview:
        """Compile current drafts before disk work starts."""

        params, patterns, invalid = OptionReader().read(option_text, limit_text, table)
        detail(
            "preview_options",
            floor_hours=params.floor_hours,
            ceiling_hours=params.ceiling_hours,
            rules=len(patterns.rules),
            left_out=len(invalid),
            min_year=patterns.min_year,
            max_year=patterns.max_year,
        )
        return PreparedPreview(
            params,
            patterns,
            frozenset(invalid),
            tuple(table),
        )

    def current(self, directory: Path, prepared: PreparedPreview, source: Path | None = None) -> CurrentPreview:
        """Preview prepared drafts and persist each rule's validity marker."""

        marked = [
            (key, description, pattern, iid in prepared.invalid)
            for iid, key, description, pattern, _dirty in prepared.table
        ]
        log_call("filenamecluster.core.operations.pipeline.cluster_directory")
        result = cluster_directory(
            directory,
            prepared.params,
            prepared.patterns,
            source=source,
            loaded=load_model(directory),
        )
        RuleLedger.mark(directory, marked)
        return CurrentPreview(result, prepared.invalid)

    @staticmethod
    def marked(options: ModelOptions) -> list[tuple[str, str, str, bool]]:
        """Every saved rule, and whether its expression cannot be compiled."""

        return [
            (key, description, pattern, bool(rule_error(description, pattern)))
            for key, description, pattern in options.rules
        ]

    @classmethod
    def _compiled(cls, options: ModelOptions):
        """Params and patterns from a saved options object, or None when they cannot be used.

        A rule that does not compile is left out. The others are kept.
        """

        try:
            params = ClusterParams(
                floor=timedelta(hours=options.floor_hours),
                ceiling=timedelta(hours=options.ceiling_hours),
            )
            rules = tuple(
                PatternRule(key, description, pattern)
                for key, description, pattern, invalid in cls.marked(options)
                if not invalid
            )
            patterns = TimestampPatterns(
                rules=rules,
                min_year=options.min_year,
                max_year=options.max_year,
                prec_clock=options.prec_clock,
                prec_epoch=options.prec_epoch,
                prec_date=options.prec_date,
            )
            patterns.compile()
        except (TypeError, ValueError, OverflowError):
            return None
        return params, patterns


trace_module(sys.modules[__name__])
