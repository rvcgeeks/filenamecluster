# Changelog

Rajas Chavadekar (rvchavadekar@gmail.com)

This file records user-visible changes to File Name Cluster. Versions follow semantic versioning.

## 0.1.3

### Changed

- The window is now classic desktop MVC. One session holds the folder, options, preview, selection, language, and log switch. The view draws that session. The controller handles clicks and asks before files move. Clustering math, the 25-round fit, the 36-hour fallback, Apply, Flatten, the seven languages, and the log switch behave as in 0.1.2.
- A folder scan, a preview, Apply, and Flatten still show the same dialogs and the same spinner sentences. After Apply, the preview stays until you choose another folder or flatten.
- `filenamecluster-model.json` is still the only model file, and it is still written in one place. Saved options and the learned boundary are unchanged.
- The package version is now `0.1.3`.

### Fixed

- Custom filename-pattern rules now carry their saved rule key explicitly during preview. Core no longer guesses a rule key from the pattern-table row name, so custom rules and their invalid markers cannot be confused with built-in rules.
- Folder scans and file moves now keep successful results separate from exceptions. Read and move failures cannot be mistaken for successful operation values.
- Option validation now reports the exact semantic field and fault to the window, while the window alone chooses the translated message. Number, whole-number, and range errors continue to show the correct option label.
- Model option drafts and pattern rows are exposed as copies, preventing a view or controller from accidentally changing session state without its normal update notification.

## 0.1.2

### Added

- `filenamecluster-model.json` now stores an `options` object beside `learned`. It holds the safety limits, year window, priorities, and filename patterns last used for that folder. Choosing the folder loads those values over the built-in defaults. A missing or unusable `options` object leaves the defaults in place and does not discard `learned`.
- The learned boundary is still fitted and reused exactly as before. Saving options does not change that workflow. Every write of the model file writes both keys.
- The About tab has a separate guide to filename regular expressions, in its own sections: what a pattern is, the little marks, the four kinds of time, two worked examples walked through one mark at a time, and the pattern table.
- The application writes a text log. Each line has a timestamp and the process id. `CALL` is written before a function runs, `ENTER` when it begins, and `EXIT` when it returns. `EVENT` marks key steps such as choosing a folder, saving the model, preview, apply, and flatten. `DETAIL` records decisions inside those functions: the clock read from a name, each pause and whether it split an event, each fit iteration, a reused or fallback boundary, and each file moved or left in place. On macOS the file is `~/Library/Logs/filenamecluster/filenamecluster.log`. On Windows it is `%LOCALAPPDATA%/filenamecluster/Logs/filenamecluster.log`. On Linux it is `$XDG_STATE_HOME/filenamecluster/filenamecluster.log`, or `~/.local/state/filenamecluster/filenamecluster.log` when `XDG_STATE_HOME` is unset. The About tab states the full path for this computer.
- The Options tab has **Write application log**, off when the app opens. Turning it on writes new log lines until it is turned off again. It is not stored in the model file.
- The window class is `FileNameClusterApp`. `ui` keeps `app.py` and `__init__.py`. Session state and language catalogs are `ui.model`. Drawing, theme, layout, calendar, timeline, and About text are `ui.view`. Clicks and opening files are `ui.controller`. `core` is unchanged in how it decides an event boundary.
- A borderless, see-through overlay plays `spinner.gif` while the window stays responsive. It appears after a folder is chosen, while that folder is read. It appears again as soon as **Apply clustering** or **Flatten clustering** is clicked, before the confirmation of which files will move, and once more after you confirm, while the files are moved. Buttons and option controls stay disabled during each of those waits. The timeline, calendar, and lists stay usable. The usual confirmation and done dialogs follow the spinner.
- The overlay has no title bar. It shows, in large bold text, exactly why you are waiting: reading saved options and calculating clusters, recalculating with your options, rechecking before Apply, moving files into event folders, looking for event folders to flatten (no clusters are calculated then), moving files back, or recalculating after a move or a failed move.
- The animation plays each frame at the delay stored in the GIF, about 30 ms, on a steady clock. The frames are decoded once per window. On macOS the overlay is a plain window with no title bar and a transparent background, so the app shows through around the animation and the text. Windows uses a color key. Linux shows the plain window background, because Tk cannot make only part of a window transparent there.

### Changed

- The package version is now `0.1.2`.
- The EM fit in `learn.py` runs `EM_ROUNDS` passes. That module variable is 25, so the fitted boundary is unchanged. Change it in `learn.py` to run more or fewer passes.
- `docs/algorithm.md` uses GitHub `math` fences for every display equation, so multiline formulas whose continuation starts with `+` are not parsed as Markdown lists. Its worked example is now a literal dry run of the pseudocode: every gap and log input, initial parameter calculation, first E-step and M-step, all 25 EM states, separation tests, quadratic coefficients and roots, final model values, and every split decision are shown using the implementation's unshortened float values.

## 0.1.1

### Added

- Filename parsing now falls back to capture-time metadata when a name has no timestamp.
- A standard-library metadata reader supports JPEG, PNG, WebP, TIFF, HEIF/AVIF, MP4, MOV, M4V, 3GP, AVI, and PDF. It reads only capture or creation time; it does not use pixels, document contents, GPS, camera details, or filesystem dates.
- Files whose capture time cannot be read remain in place and are listed in the **Skipped** tab.
- Filename regular expressions are editable in a table with Description and Pattern columns. Built-in rules remain visible, and users can add or remove custom rules.
- Double-clicking the selected orange or yellow event in the calendar, either timeline, or the cluster list opens its existing folder in a separate file-manager window. A localised warning explains when the folder has not been created.
- Double-clicking a file in **Day detail** opens it with the operating system's default application. Files already moved by Apply are resolved inside their event folder.
- Retina/high-DPI scaling was added. The app opens in a normal window rather than fullscreen. The packaged macOS app declares high-resolution capability.
- Calendar, timeline, pattern-table, metadata fallback, folder-opening, file-opening, and display behavior have automated coverage. UI tests keep Tk windows withdrawn.
- The Options tab includes a read-only table of every field in `filenamecluster-model.json`: `learned.within_hours`, `learned.between_hours`, `learned.boundary_hours`, and `learned.separated`. Values match the file. A folder with no fitted boundary shows `null`.
- The cluster list sorts by event number (`#`) or by file count (`Files`). Click a heading to sort, and click it again to reverse the direction; ↑ and ↓ show which way. The events with the most files are the major ones: sort `Files` downward to bring them to the top.

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
