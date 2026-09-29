"""Draw one session topic onto the window that is listening.

The window subscribes. These functions update that window's own widgets.
They do not change the application model.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import sys

from filenamecluster.log import trace_module
from filenamecluster.ui.model import Topic


def show_current(view, model) -> None:
    """Draw the application model as it stands."""

    if model.directory is not None:
        view.set_folder(str(model.directory))
    _options(view, model)
    if model.has_preview:
        _preview(view, model)
        _selection(view, model)
    else:
        view.show_learned(model.learned_cells())
        _status(view, model)
        view.set_actions(
            apply=model.apply_enabled,
            flatten=model.flatten_enabled,
        )
        view.show_cluster_sort((), None, model.cluster_sort)
    view.show_logging(model.logging_enabled)
    view.set_busy(model.busy)


def show_topic(view, model, topic: Topic) -> None:
    """Draw the part named by ``topic``."""

    if topic is Topic.FOLDER and model.directory is not None:
        view.set_folder(str(model.directory))
    elif topic is Topic.OPTIONS:
        _options(view, model)
    elif topic is Topic.PATTERNS:
        _patterns(view, model)
    elif topic is Topic.PREVIEW:
        _preview(view, model)
    elif topic is Topic.SELECTION:
        _selection(view, model)
    elif topic is Topic.DRAFT:
        return
    elif topic is Topic.LANGUAGE:
        view.use_language(model.language)
    elif topic is Topic.LOGGING:
        view.show_logging(model.logging_enabled)
    elif topic is Topic.STATUS:
        _status(view, model)
    elif topic is Topic.ACTIONS:
        view.set_actions(
            apply=model.apply_enabled,
            flatten=model.flatten_enabled,
        )
        _status(view, model)
    elif topic is Topic.SORT:
        view.show_cluster_sort(
            model.cluster_order(),
            model.selected_cluster,
            model.cluster_sort,
        )
    elif topic is Topic.BUSY:
        view.set_busy(model.busy)


def _options(view, model) -> None:
    view.show_option_values(model.option_drafts(), model.limit_drafts())
    _patterns(view, model)


def _patterns(view, model) -> None:
    view.show_pattern_rows(model.pattern_rows())


def _preview(view, model) -> None:
    if not model.has_preview:
        return
    events = model.shown()
    view.show_clusters(
        events,
        model.calendar_days(),
        model.cluster_order(),
        model.cluster_sort,
        model.selected_cluster,
    )
    folders, files = model.skipped()
    view.show_skipped(folders, files)
    view.show_learned(model.learned_cells())
    view.set_actions(
        apply=model.apply_enabled,
        flatten=model.flatten_enabled,
    )
    _day(view, model)
    _status(view, model)


def _status(view, model) -> None:
    view.paint_status(model.status)


def _selection(view, model) -> None:
    if not model.has_preview:
        return
    if model.selected_cluster is not None:
        view.highlight_cluster(model.selected_cluster)
    _day(view, model)


def _day(view, model) -> None:
    day = model.selected_day
    if not model.has_preview or day is None:
        view.clear_day()
        return
    view.present_day(day, model.shown(), model.day_entries(day), model.selected_cluster)


trace_module(sys.modules[__name__])
