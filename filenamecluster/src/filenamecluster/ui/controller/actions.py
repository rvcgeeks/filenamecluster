"""What the window does when the user chooses, previews, applies, or flattens.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Design: ``docs/architecture.md``.
"""

from __future__ import annotations

import sys
import threading
import tkinter as tk
from datetime import date, datetime, time, timedelta
from pathlib import Path

from tkinter import filedialog, messagebox

from filenamecluster.core.cluster import ClusterParams
from filenamecluster.core.learn import ModelOptions, load_model
from filenamecluster.core.organize import (
    flatten_cluster_folders,
    is_cluster_folder_name,
    move_into_cluster_folders,
)
from filenamecluster.core.parse import LIMIT_FIELDS, PatternRule, TimestampPatterns
from filenamecluster.core.pipeline import ClusterResult, cluster_directory
from filenamecluster.log import detail, event, log_call, set_logging_enabled, trace_module
from filenamecluster.ui.controller import files as file_ops
from filenamecluster.ui.model.i18n import LANGUAGES, file_count, set_language, t
from filenamecluster.ui.model.session import DEFAULTS, OPTIONS, AppModel, describe_model, hours
from filenamecluster.ui.view.spinner import SpinnerDialog
from filenamecluster.ui.view.window import AppView


def _compiled_options(options: ModelOptions):
    """Params and patterns from a saved options object, or None when they will not compile."""

    try:
        params = ClusterParams(
            floor=timedelta(hours=options.floor_hours),
            ceiling=timedelta(hours=options.ceiling_hours),
        )
        rules = tuple(
            PatternRule(key, description, pattern) for key, description, pattern in options.rules
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


def _preview_saved_folder(directory: Path):
    """Load the folder's saved options and scan it. No widgets are touched."""

    loaded = load_model(directory)
    options = loaded.options
    accepted = _compiled_options(options) if options is not None else None
    if options is not None and accepted is None:
        tag = "ignored"
    else:
        tag = "loaded" if accepted is not None else "defaults"
    if accepted is None:
        params, patterns = ClusterParams(), TimestampPatterns()
    else:
        params, patterns = accepted
    try:
        log_call("filenamecluster.core.pipeline.cluster_directory")
        result = cluster_directory(directory, params, patterns)
    except OSError as exc:
        return ("read_error", exc, tag, options)
    return ("ok", result, tag, options)


class AppController:
    """Turns widget actions into a preview, a move, or a flatten."""

    def __init__(self, model: AppModel, view: AppView) -> None:
        self.model = model
        self.view = view
        self._busy = False

    def choose_folder(self) -> None:
        start = Path.cwd() / "data"
        log_call("tkinter.filedialog.askdirectory")
        chosen = filedialog.askdirectory(
            parent=self.view.root,
            title=t("choose_title"),
            initialdir=start if start.is_dir() else Path.cwd(),
            mustexist=True,
        )
        if chosen:
            self.load_folder(Path(chosen))

    def load_folder(self, folder: Path) -> bool:
        if self._busy:
            return False
        self.model.directory = Path(folder)
        self.view.folder_text.set(str(self.model.directory))
        event("folder_chosen", path=str(self.model.directory))
        directory = self.model.directory
        done = {"ok": False}

        def on_done(outcome: object) -> None:
            done["ok"] = self._finish_folder_load(outcome)

        self._run_disk("busy_open", lambda: _preview_saved_folder(directory), on_done)
        return done["ok"]

    def _finish_folder_load(self, outcome: object) -> bool:
        """Apply a background folder scan to the widgets."""

        if isinstance(outcome, Exception):
            raise outcome
        kind, payload, tag, options = outcome
        directory = self.model.directory
        if tag == "loaded" and isinstance(options, ModelOptions):
            if not self._apply_saved_options(options):
                event("options_ignored", path=str(directory))
                self._reset_option_widgets()
        else:
            self._reset_option_widgets()
            if tag == "ignored":
                event("options_ignored", path=str(directory))
        if kind == "read_error":
            path, error = directory, payload
            self._remember_status(
                lambda path=path, error=error: (t("could_not_read", path=path, error=error), True)
            )
            event("preview_failed", path=str(path))
            return False
        self._show_result(payload)
        event(
            "preview_ready",
            path=str(directory),
            events=len(payload.clusters),
            files=payload.file_count,
        )
        return True

    def _reset_option_widgets(self) -> None:
        self.view.option_vars["floor"].set(hours(DEFAULTS.floor))
        self.view.option_vars["ceiling"].set(hours(DEFAULTS.ceiling))
        patterns = TimestampPatterns()
        for key, *_rest in LIMIT_FIELDS:
            self.view.limit_vars[key].set(getattr(patterns, key))
        self.view._fill_pattern_table(patterns.rules)

    def _apply_saved_options(self, options: ModelOptions) -> bool:
        try:
            ClusterParams(
                floor=timedelta(hours=options.floor_hours),
                ceiling=timedelta(hours=options.ceiling_hours),
            )
            rules = tuple(
                PatternRule(key, description, pattern)
                for key, description, pattern in options.rules
            )
            TimestampPatterns(
                rules=rules,
                min_year=options.min_year,
                max_year=options.max_year,
                prec_clock=options.prec_clock,
                prec_epoch=options.prec_epoch,
                prec_date=options.prec_date,
            ).compile()
            self.view.option_vars["floor"].set(options.floor_hours)
            self.view.option_vars["ceiling"].set(options.ceiling_hours)
            self.view.limit_vars["min_year"].set(options.min_year)
            self.view.limit_vars["max_year"].set(options.max_year)
            self.view.limit_vars["prec_clock"].set(options.prec_clock)
            self.view.limit_vars["prec_epoch"].set(options.prec_epoch)
            self.view.limit_vars["prec_date"].set(options.prec_date)
        except (tk.TclError, TypeError, ValueError, OverflowError):
            return False
        self.view._fill_pattern_table(rules, honor_saved_descriptions=True)
        event("options_loaded", path=str(self.model.directory))
        return True

    def read_params(self) -> ClusterParams:
        values: dict[str, float] = {}
        for key, label_key, *_rest in OPTIONS:
            try:
                values[key] = self.view.option_vars[key].get()
            except tk.TclError:
                raise ValueError(t("must_be_number", label=t(label_key))) from None
        return ClusterParams(
            floor=timedelta(hours=values["floor"]),
            ceiling=timedelta(hours=values["ceiling"]),
        )

    def read_patterns(self) -> TimestampPatterns:
        limits: dict[str, int] = {}
        for key, _label, _hint, low, high in LIMIT_FIELDS:
            label = t(f"limit_{key}")
            try:
                value = int(self.view.limit_vars[key].get())
            except (tk.TclError, ValueError):
                raise ValueError(t("must_be_whole", label=label)) from None
            if not low <= value <= high:
                raise ValueError(t("must_be_between", label=label, low=low, high=high))
            limits[key] = value
        self.view._close_pattern_editor(save=True)
        rules = []
        for iid in self.view.pattern_tree.get_children():
            description, pattern = self.view.pattern_tree.item(iid, "values")
            key = "" if str(iid).startswith("custom-") else str(iid)
            rules.append(PatternRule(key, str(description), str(pattern)))
        patterns = TimestampPatterns(rules=tuple(rules), **limits)
        patterns.compile()
        return patterns

    def restore_defaults(self) -> None:
        event("defaults_restored")
        self._reset_option_widgets()
        self.refresh()

    def refresh(self, on_ready=None, message_key: str = "busy_preview") -> bool:
        """Re-scan the folder and redraw every view. Nothing is moved.

        ``message_key`` names the spinner text, which says why the scan runs.
        ``on_ready`` receives True when a preview is drawn. A visible window
        runs the scan under the spinner and calls ``on_ready`` when it
        finishes. A withdrawn window, which is how the tests run, finishes
        before this method returns.
        """

        done = {"ok": False}

        def report(ok: bool) -> bool:
            done["ok"] = ok
            if on_ready is not None:
                on_ready(ok)
            return ok

        if self._busy:
            return False
        if self.model.directory is None:
            self._remember_status(lambda: (t("choose_status"), False))
            return report(False)
        try:
            params = self.read_params()
            patterns = self.read_patterns()
            detail(
                "preview_options",
                floor_hours=params.floor_hours,
                ceiling_hours=params.ceiling_hours,
                rules=len(patterns.rules),
                min_year=patterns.min_year,
                max_year=patterns.max_year,
            )
        except ValueError as exc:
            message = str(exc)
            self._remember_status(lambda message=message: (t("options_error", message=message), True))
            event("preview_rejected", path=str(self.model.directory))
            return report(False)
        directory = self.model.directory

        def work():
            log_call("filenamecluster.core.pipeline.cluster_directory")
            return cluster_directory(directory, params, patterns)

        def on_done(outcome: object) -> None:
            if isinstance(outcome, OSError):
                path, error = directory, outcome
                self._remember_status(
                    lambda path=path, error=error: (t("could_not_read", path=path, error=error), True)
                )
                event("preview_failed", path=str(path))
                report(False)
                return
            if isinstance(outcome, Exception):
                raise outcome
            self._show_result(outcome)
            event(
                "preview_ready",
                path=str(directory),
                events=len(outcome.clusters),
                files=outcome.file_count,
            )
            report(True)

        self._run_disk(message_key, work, on_done)
        return done["ok"]

    def select_cluster(self, index: int | None, show_day: bool = True) -> None:
        result = self.model.result
        if result is None or index is None or not 0 <= index < len(result.clusters):
            return
        self.model.selected_cluster = index
        cluster = result.clusters[index]
        view = self.view
        view.overview.select(index)
        view.day_view.select(index, scroll=False)
        view.calendar.select_cluster(index)
        if view.cluster_tree.selection() != (str(index),):
            view.cluster_tree.selection_set(str(index))
        view.cluster_tree.see(str(index))
        if show_day:
            self.show_day(cluster.start.date())

    def show_day(self, day: date) -> None:
        self.model.selected_day = day
        view = self.view
        view.calendar.select_day(day)
        clusters = self.model.result.clusters if self.model.result else ()
        start = datetime.combine(day, time())
        view.day_view.show(clusters, start, start + timedelta(days=1))
        if self.model.selected_cluster is not None:
            view.day_view.select(self.model.selected_cluster, scroll=False)
        entries = self.model.files_by_day.get(day, [])
        view.day_tree.delete(*view.day_tree.get_children())
        for row, (item, index) in enumerate(entries):
            number = clusters[index].number
            view.day_tree.insert(
                "", "end", iid=str(row), values=(f"{item.timestamp:%H:%M:%S}", item.name, number)
            )
        count = file_count(len(entries))
        view.day_frame.configure(text=view._day_title(day, count))

    def apply_clustering(self) -> None:
        if self._busy:
            return
        if self.model.directory is None:
            return
        self.refresh(on_ready=self._confirm_apply, message_key="busy_apply_check")

    def _confirm_apply(self, ready: bool) -> None:
        """Ask, after the preview spinner, whether to move the files."""

        if not ready or self.model.result is None or self.model.directory is None:
            return
        result = self.model.result
        if not result.clusters:
            messagebox.showinfo(
                t("nothing_to_move_title"), t("nothing_to_move_body"), parent=self.view.root
            )
            return
        already_clustered = any(is_cluster_folder_name(name) for name in result.ignored_directories)
        if already_clustered:
            prompt = t(
                "apply_update",
                path=self.model.directory,
                files=result.file_count,
                events=len(result.clusters),
            )
        else:
            prompt = t(
                "apply_create",
                events=len(result.clusters),
                path=self.model.directory,
                files=result.file_count,
            )
        log_call("tkinter.messagebox.askyesno")
        confirmed = messagebox.askyesno(t("apply"), prompt, parent=self.view.root)
        if not confirmed:
            event("apply_cancelled", path=str(self.model.directory))
            return
        directory = self.model.directory
        clusters = result.clusters
        files, events = result.file_count, len(result.clusters)

        def finish(outcome: object) -> None:
            if isinstance(outcome, (OSError, ValueError)):
                messagebox.showerror(t("could_not_move"), str(outcome), parent=self.view.root)
                event("apply_failed", path=str(directory))
                self.refresh(message_key="busy_after_error")
                return
            if isinstance(outcome, Exception):
                raise outcome
            messagebox.showinfo(
                t("applied_title"),
                t("applied_body", files=files, events=events),
                parent=self.view.root,
            )
            self.view.apply_button.configure(state="disabled")
            self.view.flatten_button.configure(state="normal")
            self._remember_status(lambda: (t("preview_stays", files=files, events=events), False))
            event("apply_finished", path=str(directory), files=files, events=events)

        log_call("filenamecluster.core.organize.move_into_cluster_folders")
        self._run_disk(
            "busy_apply",
            lambda: move_into_cluster_folders(directory, clusters),
            finish,
        )

    def flatten_clustering(self) -> None:
        if self._busy:
            return
        directory = self.model.directory
        if directory is None or not directory.is_dir():
            return

        def list_folders():
            return [
                entry.name
                for entry in directory.iterdir()
                if entry.is_dir() and is_cluster_folder_name(entry.name)
            ]

        def after_list(outcome: object) -> None:
            self._confirm_flatten(directory, outcome)

        self._run_disk("busy_flatten_check", list_folders, after_list)

    def _confirm_flatten(self, directory: Path, outcome: object) -> None:
        """Ask, after the preview spinner, whether to move the files back."""

        if isinstance(outcome, OSError):
            messagebox.showerror(t("could_not_flatten"), str(outcome), parent=self.view.root)
            return
        if isinstance(outcome, Exception):
            raise outcome
        folders = outcome
        if not folders:
            messagebox.showinfo(
                t("nothing_to_flatten_title"), t("nothing_to_flatten_body"), parent=self.view.root
            )
            return
        log_call("tkinter.messagebox.askyesno")
        confirmed = messagebox.askyesno(
            t("flatten"),
            t("flatten_confirm", folders=len(folders), path=directory),
            parent=self.view.root,
        )
        if not confirmed:
            event("flatten_cancelled", path=str(directory))
            return

        def finish(moved: object) -> None:
            if isinstance(moved, (OSError, ValueError)):
                messagebox.showerror(t("could_not_flatten"), str(moved), parent=self.view.root)
                event("flatten_failed", path=str(directory))
                self.refresh(message_key="busy_after_error")
                return
            if isinstance(moved, Exception):
                raise moved
            messagebox.showinfo(
                t("flattened_title"),
                t("flattened_body", moved=moved, name=directory.name),
                parent=self.view.root,
            )
            event("flatten_finished", path=str(directory), moved=moved)
            self.refresh(message_key="busy_after_flatten")

        log_call("filenamecluster.core.organize.flatten_cluster_folders")
        self._run_disk("busy_flatten", lambda: flatten_cluster_folders(directory), finish)

    def _show_result(self, result: ClusterResult) -> None:
        self.model.result = result
        self.model.selected_cluster = None
        self.model.files_by_day = {}
        for index, cluster in enumerate(result.clusters):
            for item in cluster.files:
                self.model.files_by_day.setdefault(item.timestamp.date(), []).append((item, index))

        view = self.view
        view.overview.show(result.clusters)
        view.calendar.set_clusters(result.clusters)

        view.cluster_tree.delete(*view.cluster_tree.get_children())
        for index, cluster in enumerate(result.clusters):
            view.cluster_tree.insert(
                "", "end", iid=str(index), values=(cluster.number, cluster.name, len(cluster.files))
            )
        view._apply_cluster_sort()

        view._fill_skipped(result)
        view._fill_model_view()

        view.apply_button.configure(state="normal" if result.clusters else "disabled")
        clustered = any(is_cluster_folder_name(name) for name in result.ignored_directories)
        view.flatten_button.configure(state="normal" if clustered else "disabled")
        if result.clusters:
            self.show_day(result.clusters[0].start.date())
        else:
            view.day_view.show(())
            view.day_tree.delete(*view.day_tree.get_children())
            view.day_frame.configure(text=t("day_detail"))
        self._remember_status(lambda result=result: (self._summary(result), False))

    def _remember_status(self, builder) -> None:
        self.model.status_builder = builder
        message, error = builder()
        self.view._set_status(message, error)

    def _summary(self, result: ClusterResult) -> str:
        event_folders = [name for name in result.ignored_directories if is_cluster_folder_name(name)]
        other_folders = [name for name in result.ignored_directories if name not in event_folders]
        included = t("event_folders_included", n=len(event_folders)) if event_folders else ""
        return t(
            "status_summary",
            events=len(result.clusters),
            files=result.file_count,
            missing=len(result.ignored_without_timestamp),
            included=included,
            folders=len(other_folders),
            model=describe_model(result.model),
        )

    def _run_disk(self, message_key: str, work, on_done) -> None:
        """Move files without freezing the window.

        A withdrawn root, which is how the tests run, does the work inline so
        the caller sees the result immediately. A visible window locks buttons
        and option controls, plays the spinner, and runs ``work`` on a
        background thread. ``root.after`` polls that thread from the normal
        event loop. ``on_done`` then runs on the UI thread with the return
        value, or with the exception object.
        """

        root = self.view.root
        if str(root.state()) == "withdrawn":
            self._busy = True
            try:
                try:
                    outcome: object = work()
                except Exception as exc:
                    outcome = exc
            finally:
                self._busy = False
            on_done(outcome)
            return
        if self._busy:
            return
        self._busy = True
        self.view.lock_inputs()
        dialog = SpinnerDialog(root, t(message_key))
        outcome_box: dict[str, object] = {}
        event("disk_work", message=message_key)

        def worker() -> None:
            try:
                outcome_box["value"] = work()
            except Exception as exc:
                outcome_box["error"] = exc
            finally:
                outcome_box["done"] = True

        def poll() -> None:
            if not outcome_box.get("done"):
                root.after(50, poll)
                return
            dialog.close()
            self.view.unlock_inputs()
            self._busy = False
            error = outcome_box.get("error")
            on_done(error if error is not None else outcome_box.get("value"))

        threading.Thread(target=worker, name="filenamecluster-disk", daemon=True).start()
        root.after(50, poll)

    def _language_changed(self, _event: tk.Event | None = None) -> None:
        chosen = self.view.language_var.get()
        code = next((code for code, name in LANGUAGES if name == chosen), "en")
        set_language(code)
        event("language_changed", language=code)
        self.view.retranslate()

    def _logging_toggled(self) -> None:
        """Apply the Options switch. Logging starts on."""

        set_logging_enabled(bool(self.view.logging_var.get()))

    def open_day_file(self, row: int) -> None:
        """Open one Day detail row with the operating system's default app."""

        if self.model.directory is None or self.model.selected_day is None:
            return
        entries = self.model.files_by_day.get(self.model.selected_day, [])
        if not 0 <= row < len(entries):
            return
        item, index = entries[row]
        path = file_ops.openable_file(self.model.directory, item, self._cluster_name(index))
        if path is None:
            messagebox.showwarning(
                t("file_missing_title"),
                t("file_missing_body", name=item.name),
                parent=self.view.root,
            )
            return
        log_call("filenamecluster.ui.controller.files.open_file")
        file_ops.open_file(path)

    def _cluster_name(self, index: int) -> str:
        result = self.model.result
        if result is None or not 0 <= index < len(result.clusters):
            return ""
        return result.clusters[index].name

    def open_cluster_folder(self, index: int) -> None:
        """Open the event folder in its own file-manager window when it exists."""

        if self.model.directory is None or self.model.result is None:
            return
        if not 0 <= index < len(self.model.result.clusters):
            return
        cluster = self.model.result.clusters[index]
        folder = self.model.directory / cluster.name
        if folder.is_dir():
            log_call("filenamecluster.ui.controller.files.open_folder_window")
            file_ops.open_folder_window(folder)
            return
        messagebox.showwarning(
            t("folder_missing_title"),
            t("folder_missing_body", name=cluster.name),
            parent=self.view.root,
        )

    def add_pattern_rule(self) -> None:
        iid = f"custom-{self.model.custom_pattern_seq}"
        self.model.custom_pattern_seq += 1
        self.view.pattern_tree.insert("", "end", iid=iid, values=(t("custom_pattern"), ""))
        self.view.pattern_tree.selection_set(iid)
        self.view.pattern_tree.see(iid)
        self.view._begin_pattern_edit(iid, "pattern")

    def remove_pattern_rule(self) -> None:
        self.view._close_pattern_editor(save=True)
        for iid in self.view.pattern_tree.selection():
            self.model.pattern_desc_dirty.discard(str(iid))
            self.view.pattern_tree.delete(iid)

    def sort_clusters(self, column: str) -> None:
        """Sort the cluster list by event number or file count, toggling direction."""

        if column not in {"number", "files"}:
            return
        current = self.model.cluster_sort
        if current is not None and current[0] == column:
            descending = not current[1]
        else:
            descending = False
        self.model.cluster_sort = (column, descending)
        event("clusters_sorted", column=column, descending=descending)
        self.view._apply_cluster_sort()

    def _tree_selected(self, event: tk.Event | None = None) -> None:
        selection = self.view.cluster_tree.selection()
        if selection and int(selection[0]) != self.model.selected_cluster:
            self.select_cluster(int(selection[0]))

    def _day_clicked(self, day: date) -> None:
        self.show_day(day)
        info = self.view.calendar.days.get(day)
        if info is not None and info.cluster is not None:
            self.select_cluster(info.cluster, show_day=False)

    def _timeline_clicked(self, when: datetime) -> None:
        self._day_clicked(when.date())

    def _tree_double(self, event: tk.Event) -> None:
        row = self.view.cluster_tree.identify_row(event.y)
        if not row or not str(row).isdigit():
            return
        index = int(row)
        if index != self.model.selected_cluster:
            return
        self.open_cluster_folder(index)

    def _day_file_double(self, event: tk.Event) -> None:
        row = self.view.day_tree.identify_row(event.y)
        if not row or not str(row).isdigit():
            return
        self.open_day_file(int(row))


trace_module(sys.modules[__name__])
