# Architecture

Rajas Chavadekar (rvchavadekar@gmail.com)

The mathematics of the boundary is in [algorithm.md](algorithm.md). This file is the shape of the program: what the pieces are, how a folder moves through them, and which classes own which data.

## High-level design

File Name Cluster is a desktop app. A person picks one folder. The app reads capture times from filenames and, when a name has none, from recognised picture, video, or PDF metadata. It learns one event boundary for that folder, draws the events, and, on confirmation, moves files into one folder per event. A later batch dropped into the same folder is clustered together with the files already filed.

When a filename has no capture time, only that time is read from the picture or video container, or from PDF CreationDate metadata; pixels, GPS, camera details, document contents, and filesystem dates are not read. Unsupported files and files with unreadable capture times are skipped. The model file `filenamecluster-model.json` sits in the chosen folder, visible. It stores the last fitted boundary at full precision under `learned`, and the safety limits, year window, priorities, and filename patterns last used for that folder under `options`. `learn` writes both keys whenever it writes the file. Fitting and reusing the boundary reads only `learned`.

```mermaid
flowchart LR
    person["Person"] --> ui["ui.FileNameClusterApp"]
    ui --> pipe["core.pipeline"]
    pipe --> parse["core.parse"]
    pipe --> exif["core.exif"]
    pipe --> cluster["core.cluster"]
    pipe --> learn["core.learn"]
    cluster --> learn
    ui --> org["core.organize"]
    parse --> folder["Chosen folder"]
    learn --> folder
    org --> folder
    ui --> views["Timeline, calendar, day detail"]
```

The workspace project is a separate installable that depends on this package and adds `stub`, which only creates or deletes empty stand-in files under `workspace/data`. It is not on the clustering path.

## Component diagram

```mermaid
flowchart TB
    subgraph presentation["Presentation"]
        app["FileNameClusterApp"]
        timeline["TimelineView"]
        calendar["CalendarView"]
        layout["TimeScale, Bar, Tick"]
        theme["theme"]
        about["about.sections"]
    end

    subgraph application["Application"]
        pipeline["cluster_directory"]
        result["ClusterResult"]
    end

    subgraph domain["Domain"]
        parse["scan_directory / parse_timestamp"]
        cluster["cluster_files"]
        learn["fit_gap_model"]
        names["name_clusters / cluster_name"]
        move["move_into_cluster_folders"]
        flatten["flatten_cluster_folders"]
        modelfile["load_model / save_model"]
    end

    subgraph storage["Folder on disk"]
        loose["Loose files"]
        events["Event folders"]
        json["filenamecluster-model.json"]
        other["Other subfolders, not entered"]
    end

    app --> timeline
    app --> calendar
    timeline --> layout
    app --> theme
    app --> about
    app --> pipeline
    app --> move
    app --> flatten
    pipeline --> result
    pipeline --> parse
    pipeline --> cluster
    pipeline --> names
    pipeline --> modelfile
    cluster --> learn
    parse --> loose
    parse --> events
    parse --> other
    modelfile --> json
    move --> events
    flatten --> loose
```

| Component | Owns | Does not own |
|---|---|---|
| `ui` | Window, options, drawing, confirmation | The decision of where an event boundary is |
| `pipeline` | One scan turned into a `ClusterResult` | Moving bytes |
| `parse` | Filename clocks, year window, top-level listing plus event-folder listing | Clustering |
| `learn` | The mixture, the boundary $\tau$, and the visible JSON | Tk, moving files |
| `cluster` | Safety limits and the join-or-split rule | How a folder is named |
| `organize` | Chronological folder names, move, flatten | The fit |
| `exif` | Capture time stored in a picture, video, or PDF. A file with no readable time is skipped | Filenames, clustering |

## Class diagram

```mermaid
classDiagram
    class TimestampPatterns {
        +rules: PatternRule[]
        +min_year
        +max_year
        +prec_clock
        +prec_epoch
        +prec_date
        +compile() CompiledTimestampPatterns
    }
    class CompiledTimestampPatterns {
        +compiled rules
        +year window
        +priorities
    }
    class PatternRule {
        +key
        +description
        +pattern
    }
    class TimestampedFile {
        +name: str
        +timestamp: datetime
        +source: str
    }
    class FolderContents {
        +files
        +directories
        +placed
    }
    class ClusterParams {
        +floor
        +ceiling
        +floor_hours
        +ceiling_hours
    }
    class GapModel {
        +within_hours
        +between_hours
        +boundary_hours
        +separated
        +splits(hours, floor, ceiling) bool
    }
    class FolderModel {
        +learned: GapModel
        +options: ModelOptions
        +with_learned()
        +with_options()
    }
    class ModelOptions {
        +floor_hours
        +ceiling_hours
        +rules
    }
    class AppModel
    class AppView
    class AppController
    class Cluster {
        +files
        +start
        +end
    }
    class NamedCluster {
        +number
        +name
        +files
        +start
        +end
    }
    class ClusterResult {
        +clusters
        +ignored_without_timestamp
        +ignored_directories
        +params
        +model
        +file_count
    }
    class FileNameClusterApp {
        +directory
        +result
        +refresh()
        +apply_clustering()
        +flatten_clustering()
    }
    class TimelineView
    class CalendarView
    class TimeScale
    class DayInfo

    TimestampPatterns --> CompiledTimestampPatterns : compile
    TimestampPatterns --> PatternRule
    FolderContents --> TimestampedFile : scan yields
    Cluster --> TimestampedFile
    NamedCluster --|> Cluster : same files, plus number and name
    ClusterResult --> NamedCluster
    ClusterResult --> GapModel
    ClusterResult --> ClusterParams
    FolderModel --> GapModel
    GapModel --> ClusterParams : splits uses floor and ceiling
    FolderModel --> ModelOptions
    FileNameClusterApp --> AppModel
    FileNameClusterApp --> AppView
    FileNameClusterApp --> AppController
    AppController --> AppModel
    AppController --> AppView
    FileNameClusterApp --> ClusterResult
    FileNameClusterApp --> TimelineView
    FileNameClusterApp --> CalendarView
    TimelineView --> TimeScale
    CalendarView --> DayInfo
```

`NamedCluster` is not a subclass in code. It carries the same files plus the folder name. The diagram shows that as an extension of the data, not as inheritance.

`TimestampedFile.source` is empty when the file sits directly in the chosen folder. When the file already lives in an event folder, `source` is `event-folder/filename` and `name` stays the filename.

## Low-level design

### Preview

`FileNameClusterApp.refresh` reads the option widgets into a `ClusterParams` and a `TimestampPatterns`, then calls `cluster_directory`. No file is moved.

```mermaid
sequenceDiagram
    participant App as FileNameClusterApp
    participant Pipe as cluster_directory
    participant Model as learn
    participant Scan as scan_directory
    participant Parse as parse_timestamp
    participant Fit as cluster_files
    participant Learn as fit_gap_model

    App->>Pipe: directory, params, patterns
    Pipe->>Model: load_model
    Model-->>Pipe: FolderModel or empty
    Pipe->>Scan: chosen folder
    Scan-->>Pipe: loose files, other folders, files inside event folders
    loop each filename
        Pipe->>Parse: name, compiled patterns
        Parse-->>Pipe: timestamp or none
        alt filename has no timestamp
            Pipe->>Pipe: read picture/video capture time
        end
    end
    Pipe->>Fit: timestamped files, params, saved model
    Fit->>Learn: log gaps strictly between floor and ceiling
    Learn-->>Fit: GapModel or none
    Fit-->>Pipe: clusters, learned boundary
    Pipe->>Model: save learned boundary and options
    Pipe-->>App: ClusterResult
    App->>App: draw timeline, calendar, lists
```

Inside `cluster_files` the steps are exactly those in [algorithm.md](algorithm.md): sort, form $g_i$, build $\mathcal{U}$, fit or reuse, then walk the gaps once.

Inside `parse_timestamp`, every enabled rule is tried. A match produces a candidate `(priority, start index, datetime)`. The highest priority wins. A tie keeps the earlier match in the name. A blank expression is off. A clock needs groups `y, mo, d, h, mi, s`. A day-month clock needs `a, b, y, h, mi`. An epoch needs `ms` and is converted with `datetime.fromtimestamp`. A date-only stamp is local midnight. Years outside the window are rejected. The Options tab presents these rules as a table of descriptions and expressions; users can add and remove custom rows.

If filename parsing returns no timestamp, `core.exif` first checks the container signature. Recognised still images are JPEG, PNG, WebP, TIFF, and HEIF/AVIF. Recognised videos are MP4, MOV, M4V, 3GP, and AVI. An embedded EXIF `DateTimeOriginal` is preferred; a video can otherwise use its `mvhd` or `IDIT` creation time. A recognised PDF uses its Info-dictionary `CreationDate` or XMP `CreateDate`. Reads are bounded to the PDF head and tail. The reader is standard-library-only and never deep-scans an arbitrary file. Failure returns `None`, and `pipeline` records that file in `ignored_without_timestamp`.

`scan_directory` lists the chosen folder only one level down. A subdirectory whose name matches an event folder is opened, and only its immediate files are taken. Any other subdirectory is recorded and not entered. `filenamecluster-model.json` is never treated as media.

### Apply

Apply calls refresh first, so the confirmation dialog describes the clustering of the folder as it is now, including any files copied in since the last preview. That read runs under `SpinnerDialog` before the question is shown. After you confirm, a second `SpinnerDialog` stays up while `move_into_cluster_folders` runs. Both waits go through `AppController._run_disk`: a daemon thread named `filenamecluster-disk`, polled with `root.after` from the normal event loop, so the operating system does not treat the app as frozen. `AppView.lock_inputs` disables every button, spinbox, checkbox, and language menu, and ignores pattern-cell edits, for that time. The timeline, calendar, and lists stay usable. When a wait finishes, the dialog closes and the controls return to their previous states. The confirmation sits between the two spinners. The done or error dialog follows the move.

Each wait passes its own message key, so the overlay says why it is up:

| Key | When | Clusters calculated |
| --- | --- | --- |
| `busy_open` | After a folder is chosen: saved options are read and every file is dated | Yes |
| `busy_preview` | Update preview, Enter in an option, Restore defaults | Yes |
| `busy_apply_check` | Apply clicked, before the question | Yes |
| `busy_apply` | Apply confirmed, files move into event folders | No |
| `busy_flatten_check` | Flatten clicked, event folders are listed before the question | No |
| `busy_flatten` | Flatten confirmed, files move back | No |
| `busy_after_flatten` | After a flatten, for the new preview | Yes |
| `busy_after_error` | After a move fails, to show what is on disk | Yes |

`SpinnerDialog` is a borderless overlay. On macOS its window style is `overlay`, with a `systemTransparent` background and `-transparent`, so the app shows through everything except the animation and the text. An override-redirect window on macOS keeps an opaque backing and paints that same color black, which is why the overlay does not use one there. Windows uses a color key. Linux shows the plain window background, because Tk cannot make only part of a window transparent there. The overlay plays each frame at the delay stored in the GIF, read by `gif_delays`, on a steady clock, and decodes the frames once per window. After a successful move the drawing stays until another folder is chosen.

```mermaid
sequenceDiagram
    participant App as FileNameClusterApp
    participant Spin as SpinnerDialog
    participant Move as move_into_cluster_folders
    participant Disk as Chosen folder

    App->>Spin: play spinner.gif while the folder is read
    App->>App: confirm which files will move
    App->>Spin: play spinner.gif again and lock buttons and options
    Note over App,Move: move runs on a background thread while the window keeps handling events
    loop each event
        Move->>Disk: create the chronological folder
        loop each file
            Move->>Disk: source is loose, or already inside an event folder
            alt already at the destination
                Move->>Move: leave it
            else destination name is free
                Move->>Disk: move
            else destination name exists and is a different file
                Move-->>App: FileExistsError
            end
        end
    end
    Move->>Disk: remove event folders this apply emptied
    App->>Spin: close
    App->>App: unlock controls, then the done or error dialog
```

Folder names:

- one calendar day: `1 24-11-2015 10.01.25 to 18.50.08`
- several days: `2 09-11-2015 20.49.41 to 12-11-2015 10.24.42`

The leading number is the chronological index starting at 1, unpadded. The clock uses dots so the name is a legal folder name.

### Flatten

Flatten uses the same two spinners as Apply. The first plays while the event folders are listed, before the confirmation that files will move back. The second plays, with the message for moving files back, after you confirm. `flatten_cluster_folders` considers only immediate subfolders whose names match that pattern. It plans every move first. If any filename already exists in the chosen folder, nothing is moved. Otherwise each file is moved up and the event folder is removed when `rmdir` succeeds. A nested directory left inside an event folder keeps that folder on disk. Other subfolders are not touched. The model JSON stays, because it is not inside an event folder.

### A later batch

Copying files into the chosen folder does not start a background watcher. The next `refresh` (Choose folder, Update preview, or the refresh at the start of Apply) rebuilds one sequence:

1. Loose timestamped files in the chosen folder.
2. Timestamped files already inside event folders.

That sequence is fitted again. A new file joins an event when its neighbouring gaps do not split. It starts an event when they do. Apply then moves only the files whose current path is not already the destination, and drops event folders that became empty because their span, and therefore their name, changed.

## Descriptive write-up

The package splits along the three jobs the work actually has.

**Read a clock from a name.** `parse` is the only place a filename becomes a `datetime`. The expressions, the year window, and the priorities are data on `TimestampPatterns`, edited from the Options tab and compiled once per scan. Compilation fails closed: a bad expression or a missing named group raises `ValueError` with the field label, and the preview does not change.

**Decide the events.** `learn` is a pure function from a list of log-hours to a `GapModel` or `None`. `cluster` wraps that with the floor, the ceiling, the 36-hour fallback, and the reuse of a saved boundary. Neither module imports Tk or touches the filesystem. That is why the same function can cluster a camera roll held only in memory.

**Put the events on disk and on screen.** `organize` knows the folder-name grammar and the move rules. `pipeline` is the one function the window calls to go from a path to a `ClusterResult`, and it is also the function that writes the JSON. `ui` draws that result and asks before `organize` moves anything. Reading a chosen folder, preparing that question, and moving the files each run off the UI thread, with `spinner.gif` on screen, so a large folder does not look frozen.

The window is split so a failure is easier to place. `ui.model.session.AppModel` holds the chosen folder, the last preview, and the selection. `ui.view.window.AppView` builds the widgets. `ui.controller.actions.AppController` loads a folder, refreshes, applies, flattens, and opens a result. `ui.controller.files` asks the operating system to open a file or a folder. `FileNameClusterApp` in `ui/app.py` composes those three and forwards attribute lookup to them. `core` still decides the event boundary. `filenamecluster.log` writes `CALL`, `ENTER`, `EXIT`, `EVENT`, and `DETAIL` lines, each with a timestamp and the process id, to the operating system's application-log directory. `DETAIL` is a decision or an intermediate value inside a function.

The window is one `FileNameClusterApp` on one `tk.Tk`. The timeline and the calendar share cluster indices. Clicking a bar, a calendar day, or a row selects the same event. The cluster list sorts by event number (`#`) or by file count (`Files`). Clicking a heading toggles ascending and descending, shown as ↑ and ↓. The events with the most files are the major ones: sorting `Files` downward brings them to the top. Double-clicking the selected orange or yellow event opens its existing folder in a separate file-manager window; a missing folder produces a localised warning. Double-clicking a Day detail row resolves the file's current loose or event-folder path and asks the operating system to open it with the default application. The timeline scale is in `layout.TimeScale`: one day is a constant number of pixels, so a gap on screen is the gap in time. Zoom changes that constant. The calendar colours a day by the event that owns it.

Options are not a second clustering mode. They are the inputs of the same functions: `ClusterParams.floor`, `ClusterParams.ceiling`, and the fields of `TimestampPatterns`. Restore defaults writes the built-in values back into the widgets and refreshes. The tab keeps filename patterns across the top. Below that, a horizontal split holds three resizable columns: safety limits, the year window, and the read-only model table. The horizontal sash sets how tall the pattern row is. The two vertical sashes set the column widths. Every pane stretches when the window grows. There is no scrolling column of stacked sections.

The same tab shows a read-only table of `filenamecluster-model.json`. The rows are `learned.within_hours`, `learned.between_hours`, `learned.boundary_hours`, and `learned.separated`. Values come from `ClusterResult.model` after a preview, formatted with `json.dumps` so the digits match the file. `true`, `false`, and `null` are the JSON literals. Before a folder is chosen the cells show an em dash. The table has no editor. A language change refreshes the headings and the meaning column.

`main` enables process DPI awareness before creating Tk, and sharpens Tk scaling against the display backing scale. The app opens as a normal 1360x880 window. The packaged macOS app also declares high-resolution capability. Tests use withdrawn Tk roots and suppress requests that could map a test window.

Failure stays local. An unreadable folder sets the status line. A move that would overwrite stops and reports `FileExistsError` or `OSError`. A model file that cannot be written is skipped; the preview still appears. A model file that is not valid JSON, or whose `learned` object is missing fields, loads as no saved boundary. A missing or unusable `options` object leaves the built-in defaults in place and does not discard a valid `learned` object. A log file that cannot be opened does not stop the preview.

`ui` contains `app.py` and `__init__.py`. The calendar is `ui/view/calendar.py`. The timeline, its geometry, the theme, and the About text are the other modules in `ui/view`. Language catalogs are `ui/model/i18n`. Session state is `ui/model/session.py`. Clicks and file opening are `ui/controller`. Model persistence lives in `core/learn.py`; there is no separate `model_file.py`. The only build driver is `filenamecluster/build.py`, beside `pyproject.toml`.

The icon shown by the window is `filenamecluster/src/filenamecluster/ui/assets/icon.svg`, rasterized to `icon.png` beside it because Tk’s `PhotoImage` loads the PNG. `spinner.gif` in that same folder is the animation played by `SpinnerDialog` after a folder is chosen and both before and after the Apply and Flatten confirmations. The frozen build copies both files in next to the package.

## UI element map

Every control on the window, the module that builds it, and the function that runs when it is used. `FileNameClusterApp` in `ui/app.py` builds `AppModel`, `AppView`, and `AppController`, then forwards attribute lookup through the controller, the view, and the model. Words on the widgets come from `ui/model/i18n`. A language change calls `AppController._language_changed`, then `i18n.set_language`, then `AppView.retranslate`.

### Window shell

| What you see | Built by | What runs |
| --- | --- | --- |
| Process DPI awareness, before the window exists | `ui/app.py` `main` | `ui.view.theme.prepare_process_dpi` |
| Window, 1360×880, minimum 1040×680 | `AppView.build` | `tk.Tk` created in `main`; `root.mainloop` |
| Window icon | `AppView._install_icon` | `tk.PhotoImage` of `ui/assets/icon.png` from `_icon_path` |
| Title bar text and the large title | `AppView.build`, `AppView._build_header` | Catalog key `app_title`. `retranslate` sets `root.title` again |
| Folder path under the title | `AppView._build_header` label bound to `folder_text` | `AppController.load_folder` writes the path. With no folder, `retranslate` writes the empty-state phrase |
| Language label | `AppView._build_header` | Label only |
| Language menu | `AppView._build_header` combobox bound to `language_var` | `<<ComboboxSelected>>` → `AppController._language_changed` → `i18n.set_language` → `AppView.retranslate`. Values are `i18n.LANGUAGES` |
| Choose folder… | `AppView._build_header` | `AppController.choose_folder` → `tkinter.filedialog.askdirectory`. After a folder is chosen, `load_folder` plays the spinner and runs `_preview_saved_folder` on the background thread |
| Flatten clustering | `AppView._build_header` | Starts disabled. `AppController.flatten_clustering` shows the spinner, then `_confirm_flatten` asks, then `_run_disk` shows the spinner again for the move |
| Apply clustering | `AppView._build_header` | Starts disabled. `AppController.apply_clustering` shows the spinner, then `_confirm_apply` asks, then `_run_disk` shows the spinner again for the move |
| Status line along the bottom | `AppView.build` label bound to `status_text` | `AppView._set_status`. The sentence is stored on `AppModel.status_builder` by `AppController._remember_status` |
| Four tabs | `AppView._add_tab` on `ttk.Notebook` | Tab titles refresh in `AppView.retranslate` |

After a scan, `AppController._show_result` fills the timeline, calendar, cluster list, day detail, skipped list, and learned-model table, and enables Apply when there is at least one event. Flatten is enabled when the folder already contains an event-folder name.

### Clusters tab

The tab is `AppView._build_clusters_tab`. The three lower panes sit in a horizontal `ttk.Panedwindow`. Dragging a sash is Tk; there is no app handler on those sashes.

| What you see | Built by | What runs |
| --- | --- | --- |
| Timeline frame and its caption | `AppView._build_clusters_tab` | Caption only |
| Whole-folder timeline | `ui.view.timeline.TimelineView`, stored as `overview` | `TimelineView.show` from `_show_result`. Bars and ticks are drawn by `TimelineView._draw` using `ui.view.layout.TimeScale` |
| − | `TimelineView.__init__` | `TimelineView.zoom_out` |
| + | `TimelineView.__init__` | `TimelineView.zoom_in` |
| Fit | `TimelineView.__init__` | `TimelineView.fit` |
| Zoom caption | `TimelineView` label | `timeline._describe_zoom`, refreshed by `TimelineView.retranslate` |
| Timeline canvas | `TimelineView` | Click on a bar: `TimelineView._clicked` → `on_select` → `AppController.select_cluster`. Click on empty scale: `_clicked` → `on_time` → `AppController._timeline_clicked` → `_day_clicked`. Double-click the selected bar: `TimelineView._double` → `on_open` → `AppController.open_cluster_folder` |
| Timeline horizontal scrollbar | `TimelineView` | Canvas `xview` |
| Timeline vertical scrollbar | `TimelineView` | Canvas `yview` |
| Plain mouse wheel | `TimelineView._wheel` | Scrolls sideways. Shift-wheel uses the same handler |
| Ctrl or Cmd with the wheel | `TimelineView._zoom_wheel` | Zooms. Button-4 and Button-5 call `TimelineView._scroll` |
| Calendar frame | `AppView._build_clusters_tab` | `ui.view.calendar.CalendarView` |
| ◀◀ | `CalendarView.__init__` | `CalendarView.previous_event_month` |
| ◀ | `CalendarView.__init__` | `CalendarView.move(-1)` via `calendar.shift_month` |
| Month title | `CalendarView` label | `CalendarView.show_month` / `redraw` |
| ▶ | `CalendarView.__init__` | `CalendarView.move(1)` |
| ▶▶ | `CalendarView.__init__` | `CalendarView.next_event_month` |
| Day cells | `CalendarView.redraw` and `_draw_cell` | Colour and counts come from `calendar.summarize_days`. Click: `CalendarView._clicked` → `day_at` → `on_day` → `AppController._day_clicked` → `show_day`, and `select_cluster` when that day belongs to an event. Double-click the selected event’s day: `CalendarView._double` → `on_open` → `open_cluster_folder` |
| Cluster list frame | `AppView._build_clusters_tab` | Caption only |
| # heading | `AppView._tree` column `number` | `AppController.sort_clusters`. Arrow text is `AppView._cluster_heading_text` |
| Folder name heading | column `name` | Heading only. It does not sort |
| Files heading | column `files` | `AppController.sort_clusters`. Row order is `AppView._apply_cluster_sort` using `_cluster_sort_key` |
| Cluster rows | `AppController._show_result` inserts them | Select: `<<TreeviewSelect>>` → `AppController._tree_selected` → `select_cluster`. Double-click the selected row: `AppController._tree_double` → `open_cluster_folder` |
| Cluster list scrollbar | `AppView._tree` | Tree `yview` |
| Day detail frame | `AppView._build_clusters_tab`, stored as `day_frame` | Caption from `AppView._day_title` inside `AppController.show_day` |
| Day timeline | second `TimelineView`, stored as `day_view` | Same zoom, wheel, and drawing as the overview. Clicking a bar calls `select_cluster` with `show_day=False`. Double-click opens the folder through `open_cluster_folder` |
| Time, File, and Event columns | `day_tree` from `AppView._tree` | Filled by `AppController.show_day` from `AppModel.files_by_day` |
| A file row | `day_tree` | Double-click: `AppController._day_file_double` → `open_day_file` |
| Day-detail scrollbar | `AppView._tree` | Tree `yview` |

`select_cluster` keeps one index on the overview, the day timeline, the calendar, and the cluster list. `show_day` sets `AppModel.selected_day`, calls `CalendarView.select_day`, and redraws `day_view` for that calendar day.

### Options tab

The tab is `AppView._build_options_tab`. The pattern block and the three columns are `tk.PanedWindow` panes from `AppView._split`.

| What you see | Built by | What runs |
| --- | --- | --- |
| Update preview | bottom button bar | `AppController.refresh` → `read_params` and `read_patterns` → `core.pipeline.cluster_directory` |
| Restore defaults | bottom button bar | `AppController.restore_defaults` → `_reset_option_widgets` → `refresh`. Logging stays as it is |
| Write application log | `logging_switch` checkbox, `logging_var`, off at startup | `AppController._logging_toggled` → `filenamecluster.log.set_logging_enabled`. This is not written into the model file |
| Horizontal sash above the three columns | `options_rows` | Tk resize. `AppView._reflow` and `_flowing_help` wrap the hint text |
| Filename patterns caption and help | pattern `LabelFrame` | Help text only |
| Description and Pattern columns | `pattern_tree` | Double-click: `AppView._edit_pattern_cell` → `_begin_pattern_edit` |
| Cell editor | temporary `ttk.Entry` | Return or focus-out: commit inside `_begin_pattern_edit`. Escape: cancel. A changed built-in description is recorded on `AppModel.pattern_desc_dirty` |
| Add pattern | button under the table | `AppController.add_pattern_rule` inserts a row and opens the editor |
| Remove pattern | button under the table | `AppController.remove_pattern_rule` |
| Pattern scrollbar | `AppView._tree` | Tree `yview` |
| Vertical sashes between the three columns | `options_columns` | A sash drag calls `AppView._mark_columns_user_sized` and stays put. Until then, `Configure` → `_balance_options_grid` → `_finish_equal_columns` → `_place_equal_columns`. `main` also schedules `_finish_equal_columns` once the window is idle |
| Never split before | spinbox `option_vars["floor"]` | `AppController.read_params` → `ClusterParams.floor`. Enter calls `refresh` |
| Always split after | spinbox `option_vars["ceiling"]` | `read_params` → `ClusterParams.ceiling`. Enter calls `refresh` |
| Safety-limit hints | labels under the spinboxes | `AppView._reflow` wraps them |
| Minimum year | `limit_vars["min_year"]` | `AppController.read_patterns` → `TimestampPatterns.min_year` |
| Maximum year | `limit_vars["max_year"]` | `read_patterns` → `TimestampPatterns.max_year` |
| Clock priority | `limit_vars["prec_clock"]` | `read_patterns` → `TimestampPatterns.prec_clock` |
| Epoch priority | `limit_vars["prec_epoch"]` | `read_patterns` → `TimestampPatterns.prec_epoch` |
| Date priority | `limit_vars["prec_date"]` | `read_patterns` → `TimestampPatterns.prec_date` |
| Year-window hints | labels under those spinboxes | `AppView._reflow` |
| Learned model caption and help | model `LabelFrame` | Help text only. The table does not edit |
| Parameter, Value, Meaning | `model_tree` | `AppView._fill_model_view` reads `ClusterResult.model`. The four rows are `learned.within_hours`, `learned.between_hours`, `learned.boundary_hours`, and `learned.separated` |
| Learned-model scrollbar | `AppView._tree` | Tree `yview` |

Every safety-limit and year-window spinbox is built by `AppView._option_row`. Enter in any of them calls `refresh`.

Choosing a folder calls `_preview_saved_folder` on the background thread. That loads `core.learn.load_model`, scans with the saved options when they compile, and otherwise uses the built-in defaults. Back on the UI thread, `_finish_folder_load` calls `_apply_saved_options` when the saved options were used. `cluster_directory` writes both `learned` and `options` through `core.learn.save_model`.

### Skipped tab

| What you see | Built by | What runs |
| --- | --- | --- |
| Intro sentence | `AppView._build_skipped_tab` | Label only |
| Name and Reason columns | `skipped_tree` | `AppView._fill_skipped` |
| A subfolder row | filled from `ClusterResult.ignored_directories` | Event-folder names use one reason; any other subfolder uses the other. `core.organize.is_cluster_folder_name` chooses |
| A file row | filled from `ClusterResult.ignored_without_timestamp` | The file had no usable filename clock and no usable picture, video, or PDF creation time |
| Scrollbar | `AppView._tree` | Tree `yview` |

### About tab

| What you see | Built by | What runs |
| --- | --- | --- |
| Scrolling text | `AppView._build_about_tab` `tk.Text`, tag `heading` | `AppView._fill_about` → `ui.view.about.sections` |
| Vertical scrollbar | `AppView._build_about_tab` | Text `yview` |

`about.sections` walks `about.SECTION_KEYS`. Each heading and body is a catalog string. The logging body receives the path from `filenamecluster.log.log_path`. Regex bodies are passed through `str.format` so brace counts in the recipes stay literal. The sections, in order, are: what this does, how to use it, reading the views, folder names, which files are used, options, filename patterns, the little marks, four kinds of time, the camera-photo example, the scanned-page example, the pattern table, the application log, and author and documents.

### Dialogs

| What you see | Opened by | What runs next |
| --- | --- | --- |
| Choose the folder to cluster | `AppController.choose_folder` | After a folder is chosen, the spinner plays while `load_folder` reads it |
| Apply confirmation | `AppController._confirm_apply` | Shown after the reading spinner. Yes → a second `SpinnerDialog` and `core.organize.move_into_cluster_folders`. No → the preview stays |
| Nothing to move | `apply_clustering` when there are no events | Dialog only |
| Could not move | `apply_clustering` on `OSError` or `ValueError` | Then `refresh` |
| Applied | `apply_clustering` after a successful move | Apply is disabled. Flatten is enabled. The drawings stay |
| Wait overlay, with `spinner.gif` | `ui.view.spinner.SpinnerDialog`, opened by `AppController._run_disk` | On macOS an `overlay` window with a `systemTransparent` background, so there is no black box and no title bar. Windows uses `-transparentcolor`. Linux uses `overrideredirect` and the plain background. Large bold text from the `busy_*` key passed to `_run_disk`. Frame delays come from `gif_delays`. It does not grab the rest of the window |
| Buttons, spinboxes, the logging switch, and the language menu | `AppView.lock_inputs` | Disabled while the spinner is up. Pattern cells ignore double-click. `AppView.unlock_inputs` restores the earlier state, including a button that was already disabled |
| Flatten confirmation | `AppController._confirm_flatten` | Shown after the reading spinner. Yes → a second `SpinnerDialog` and `core.organize.flatten_cluster_folders` |
| Nothing to flatten | `flatten_clustering` when no event folder is present | Dialog only |
| Could not flatten | `flatten_clustering` on `OSError` or `ValueError` | Then `refresh` |
| Folder has not been created | `AppController.open_cluster_folder` when `directory / cluster.name` is not a directory | `ui.controller.files.open_folder_window` when it is |
| File cannot be opened | `AppController.open_day_file` when `files.openable_file` returns nothing | `ui.controller.files.open_file` when a path exists |

`open_file` uses `open` on macOS, `os.startfile` on Windows, and `xdg-open` elsewhere. `open_folder_window` uses Finder via `osascript` on macOS, Explorer on Windows, and `xdg-open` elsewhere. The path of a file already moved by Apply is resolved in `files.openable_file` with `core.organize._source_path`.

### Paint and type, shared by the controls

| Concern | Module | Function |
| --- | --- | --- |
| Colours, clam theme, fonts | `ui.view.theme` | `apply`, called from `AppView.__init__`. `sharpen` runs inside `apply` |
| Script-specific fonts after a language change | `ui.view.theme` | `use_script`, called from `AppView.retranslate` |
| One day in a constant number of pixels | `ui.view.layout` | `TimeScale`, plus the tick iterators it uses |
| Session: folder, result, selection, sort, dirty pattern descriptions | `ui.model.session` | `AppModel` |
| Hours shown in the safety-limit spinboxes | `ui.model.session` | `hours` |
| Learned-boundary sentence on the status line | `ui.model.session` | `describe_model`, used by `AppController._summary` |

## Troubleshooting

| What you see | What it means | What to try | Where it lives |
| --- | --- | --- | --- |
| The status line says to choose a folder, and Apply stays disabled | No folder is loaded, so `refresh` returns without scanning | Choose folder… | `AppController.refresh`, `choose_folder` |
| Update preview does not change the drawings, and the status line names a pattern row | That recipe does not compile, or its named groups are not one of the four kinds | Fix the recipe, or clear it to turn the row off. The previous preview is kept | `AppController.read_patterns`, `core.parse` compile, `AppController.refresh` |
| A spinbox is blank or out of range, and the status line says so | The safety limits, years, or priorities could not be read | Type a number inside the range shown for that field, then Update preview | `AppController.read_params`, `read_patterns` |
| A stamp you can see in the name is ignored | The year is outside Minimum year and Maximum year, or the clock is impossible, such as month 13 | Widen the year window or correct the name, then Update preview | `core.parse` year window and clock checks; spinboxes in `AppView._build_options_tab` |
| A file is on the Skipped tab | The name had no usable clock, and picture, video, or PDF creation time could not be read. A row that is a folder was not entered | Rename to a supported pattern, or leave the file. Other subfolders are never entered. Event folders are listed because their files were read from inside them | `AppView._fill_skipped`, `core.pipeline`, `core.exif`, `core.parse.scan_directory` |
| Two events should have been one, or one event should have been two | The learned boundary, or a safety limit, split or kept that pause | Raise Never split before to force short pauses together. Lower Always split after to force long pauses apart. Update preview. The boundary itself is still fitted from pauses | `AppController.read_params`, `core.cluster`, `core.learn.fit_gap_model` |
| The learned-model table shows null | This folder has no saved boundary yet, usually because there were too few pauses to fit one | Preview a folder with more gaps. The four cells are only `learned` | `AppView._fill_model_view`, `core.learn.load_model` |
| An old model file has no options, or options look wrong | Missing or unusable `options` fall back to the built-in defaults. A valid `learned` object is kept | Update preview writes a fresh `options` object beside `learned` | `core.learn.load_model`, `_preview_saved_folder`, `AppController._finish_folder_load` |
| Choosing the folder does not restore the limits you typed last time | Those values are written when a preview or apply saves the model. A preview that fails on a bad recipe does not save | Make the recipes valid and Update preview | `core.pipeline.cluster_directory`, `core.learn.save_model` |
| The model file is missing after a preview, or the status mentions that it could not be saved | The preview still stands. Saving the JSON failed and was skipped | Check that the folder is writable | `core.learn.save_model`, `core.pipeline` |
| The spinner has a solid box behind it on Linux | Tk on X11 cannot make only part of a window transparent | Expected. macOS and Windows show only the animation and the text | `ui.view.spinner._transparent_background` |
| The operating system says the app is not responding after Choose folder, Apply, or Flatten | The read or the move used to run on the UI thread, so the event loop stopped | The Please wait dialog plays `spinner.gif` while the folder is read, before either confirmation, and again after you confirm while files move. `AppController._run_disk` does that work on a background thread and polls it with `root.after`. Buttons and option controls are locked. The timeline, calendar, and lists still respond | `ui.view.spinner.SpinnerDialog`, `AppView.lock_inputs`, `core.pipeline.cluster_directory`, `core.organize` |
| Apply asks, then says it could not move | A destination name already exists as a different file, or the disk rejected the move | Move or rename the blocking file, then Apply again. The error dialog is followed by a fresh preview | `core.organize.move_into_cluster_folders`, `AppController.apply_clustering` |
| Flatten says it could not flatten | A file inside an event folder already has the same name in the chosen folder, so no file was moved | Rename one of the two, then Flatten again | `core.organize.flatten_cluster_folders` |
| Flatten says there is nothing to flatten | No immediate subfolder matches an event-folder name | Apply first, or the folders were already flattened | `AppController.flatten_clustering`, `is_cluster_folder_name` |
| Double-clicking an event says the folder has not been created | Apply has not created that folder yet. The preview only draws | Apply clustering, then double-click again | `AppController.open_cluster_folder` |
| Double-clicking a file says it cannot be opened | The loose path and the event-folder path are both missing | The file was removed after the preview. Update preview | `AppController.open_day_file`, `ui.controller.files.openable_file` |
| Double-click opens the wrong application, or no window | The operating system chooses the application | Change the system association for that file type. The app calls `open`, `os.startfile`, or `xdg-open` | `ui.controller.files.open_file`, `open_folder_window` |
| The log file has no new lines | Write application log is off, or the log directory could not be created. A failed log never stops the preview | Turn the switch on. It starts off, and it is not stored in the model file. The About tab shows this computer’s full path | `AppController._logging_toggled`, `filenamecluster.log.configure`, `log_path` |
| The window text is in the wrong language | The menu selects a catalog. Unknown codes stay on English | Pick the language again. Catalogs must share keys with English or the app refuses to start | `AppController._language_changed`, `ui.model.i18n` |
| Type looks soft on a high-resolution display | Tk scaling did not match the display | `main` calls `prepare_process_dpi` before creating Tk, and `theme.apply` calls `sharpen` | `ui.view.theme` |
