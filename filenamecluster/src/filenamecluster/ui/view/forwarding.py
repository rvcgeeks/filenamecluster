"""One-line forwards from the window to the section that owns the widget.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import sys

from filenamecluster.log import trace_module
from filenamecluster.ui.controller import Notice, Question, Transfer
from filenamecluster.ui.model import NameClash


class ViewForwarding:
    """Methods ``AppView`` inherits so each section stays behind one window."""

    def lock_inputs(self) -> None:
        self.kit.lock_inputs()

    def unlock_inputs(self) -> None:
        self.kit.unlock_inputs()

    def finish_equal_columns(self) -> None:
        self.columns.finish()

    def _place_equal_columns(self, width: int) -> None:
        self.columns.place(width)

    def flush_edits(self) -> None:
        self.patterns.flush_edits()
        self.clusters.flush_rename()

    def close(self) -> None:
        """Store a changed model, then close the window."""

        self.patterns.flush_edits()
        self.clusters.folder_names.close(save=True)
        self.actions.store_on_close()
        self.root.destroy()

    def validate_pattern(self, iid: str) -> None:
        self.patterns.validate(iid)

    def pattern_marked(self, iid: str) -> bool:
        return self.patterns.marked(iid)

    def _begin_pattern_edit(self, iid: str, column: str) -> None:
        self.patterns.begin_edit(iid, column)

    @property
    def _pattern_editor(self):
        return self.patterns._pattern_editor

    def show_option_values(self, options: dict[str, str], limits: dict[str, str]) -> None:
        self.options.show_values(options, limits)

    def show_logging(self, enabled: bool) -> None:
        self.options.show_logging(enabled)

    def show_learned(self, cells) -> None:
        self.options.show_learned(cells)

    def show_pattern_rows(self, rows) -> None:
        self.patterns.show_rows(rows)

    def show_clusters(self, clusters, days, order, sort, selected) -> None:
        self.clusters.show_clusters(clusters, days, order, sort, selected)

    def show_cluster_sort(self, order, selected, sort) -> None:
        self.clusters.show_cluster_sort(order, selected, sort)

    def highlight_cluster(self, index: int) -> None:
        self.clusters.highlight_cluster(index)

    def present_day(self, day, clusters, entries, selected) -> None:
        self.clusters.present_day(day, clusters, entries, selected)

    def clear_day(self) -> None:
        self.clusters.clear_day()

    def show_skipped(self, folders, files) -> None:
        self.info.show_skipped(folders, files)

    def paint_status(self, status) -> None:
        self.messages.paint_status(status)

    def ask(self, question: Question) -> bool:
        return self.messages.question(question)

    def ask_transfer(self, question: Question) -> Transfer | None:
        return self.messages.transfer(question)

    def resolve_clash(self, clash: NameClash) -> None:
        self.messages.resolve_clash(clash)

    def tell(self, notice: Notice) -> None:
        self.messages.present(notice)

    def tell_info(self, title_key: str, body_key: str, *, timed: bool = False, **fields: object) -> None:
        self.messages.tell_info(title_key, body_key, timed=timed, **fields)

    def tell_error(self, title_key: str, body: str, *, timed: bool = False) -> None:
        self.messages.tell_error(title_key, body, timed=timed)

    def tell_warning(self, title_key: str, body_key: str, **fields: object) -> None:
        self.messages.tell_warning(title_key, body_key, **fields)

    def choose_directory(self, initial, title_key: str = "choose_title") -> str:
        return self.messages.choose_directory(initial, title_key)

    def _on_logging(self) -> None:
        self.options.on_logging()

    def _on_cluster_selected(self, _event: object | None = None) -> None:
        self.clusters.on_selected(_event)

    def _on_cluster_opened(self, event) -> None:
        self.clusters.on_opened(event)

    def _on_day_file(self, event) -> None:
        self.clusters.on_day_file(event)


trace_module(sys.modules[__name__])
