# Changelog

Rajas Chavadekar (rvchavadekar@gmail.com)

This file records user-visible changes to File Name Cluster. Versions follow semantic versioning.

## 0.1.1

### Added

- Filename parsing now falls back to capture-time metadata when a name has no timestamp.
- A standard-library metadata reader supports JPEG, PNG, WebP, TIFF, HEIF/AVIF, MP4, MOV, M4V, 3GP, AVI, and PDF. It reads only capture or creation time; it does not use pixels, document contents, GPS, camera details, or filesystem dates.
- Files whose capture time cannot be read remain in place and are listed in the **Skipped** tab.
- Filename regular expressions are editable in a table with Description and Pattern columns. Built-in rules remain visible, and users can add or remove custom rules.
- Double-clicking the selected orange or yellow event in the calendar, either timeline, or the cluster list opens its existing folder in a separate file-manager window. A localised warning explains when the folder has not been created.
- Double-clicking a file in **Day detail** opens it with the operating system's default application. Files already moved by Apply are resolved inside their event folder.
- Retina/high-DPI scaling and fullscreen startup were added. The packaged macOS app declares high-resolution capability.
- Calendar, timeline, pattern-table, metadata fallback, folder-opening, file-opening, and display behavior have automated coverage. UI tests keep Tk windows withdrawn.
- The Options tab includes a read-only table of every field in `filenamecluster-model.json`: `learned.within_hours`, `learned.between_hours`, `learned.boundary_hours`, and `learned.separated`. Values match the file. A folder with no fitted boundary shows `null`.

### Changed

- `ui/calendar_view.py` was renamed to `ui/calendar.py`.
- Model persistence moved from `core/model_file.py` into `core/learn.py`.
- The build command is `uv run python build.py`; the obsolete `src/filenamecluster/build.py` wrapper and package build entry point were removed.
- About text and project documentation now describe media timestamp fallback, custom regex rows, open-on-double-click behavior, display scaling, and skipped files.
- The package version is now `0.1.1`.
- The Options tab puts filename patterns across the top. Safety limits, the year window, and the learned model share three resizable columns underneath.

### Repository

- `workspace/data/` is retained through `.gitkeep`; generated contents remain ignored.

## 0.1.0 — first release

- Introduced the Tkinter desktop application for grouping timestamped photos and videos into chronological event folders.
- Parsed built-in filename clock, numeric-date, Unix-millisecond, and date-only patterns with configurable year and priority settings.
- Learned a folder-specific event boundary from log time gaps, with safety limits, a deterministic fallback, and a visible `filenamecluster-model.json`.
- Added to-scale overview and day timelines, calendar navigation, cluster and skipped-file lists, seven UI languages, Apply, incremental re-Apply, and Flatten.
- Added safe move planning that avoids overwrites, chronological event-folder names, packaging for Windows, macOS, and Linux, and automated tests with an 80% coverage requirement.
