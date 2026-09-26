# Architecture

Rajas Chavadekar (rvchavadekar@gmail.com)

The mathematics of the boundary is in [algorithm.md](algorithm.md). This file is the shape of the program: what the pieces are, how a folder moves through them, and which classes own which data.

## High-level design

File Time Cluster is a desktop app. A person picks one folder. The app reads capture times out of filenames, learns one event boundary for that folder, draws the events, and, on confirmation, moves files into one folder per event. A later batch dropped into the same folder is clustered together with the files already filed.

Nothing in that path opens an image. The model file `filetimecluster-model.json` sits in the chosen folder, visible, and stores the last fitted boundary at full precision.

```mermaid
flowchart LR
    person["Person"] --> ui["ui.ClusterApp"]
    ui --> pipe["core.pipeline"]
    pipe --> parse["core.parse"]
    pipe --> model["core.model_file"]
    pipe --> cluster["core.cluster"]
    cluster --> learn["core.learn"]
    ui --> org["core.organize"]
    parse --> folder["Chosen folder"]
    model --> folder
    org --> folder
    ui --> views["Timeline, calendar, day detail"]
```

The workspace project is a separate installable that depends on this package and adds `stub`, which only creates or deletes empty stand-in files under `workspace/data`. It is not on the clustering path.

## Component diagram

```mermaid
flowchart TB
    subgraph presentation["Presentation"]
        app["ClusterApp"]
        timeline["TimelineView"]
        calendar["CalendarView"]
        layout["TimeScale, Bar, Tick"]
        theme["theme"]
        about["about.SECTIONS"]
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
        json["filetimecluster-model.json"]
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
| `learn` | The mixture and the boundary $\tau$ | Files, folders, Tk |
| `cluster` | Safety limits and the join-or-split rule | How a folder is named |
| `organize` | Chronological folder names, move, flatten | The fit |
| `model_file` | Reading and writing the visible JSON | Deciding $\tau$ |

## Class diagram

```mermaid
classDiagram
    class TimestampPatterns {
        +clock and date expressions
        +min_year
        +max_year
        +prec_clock
        +prec_epoch
        +prec_date
        +compile() CompiledTimestampPatterns
    }
    class CompiledTimestampPatterns {
        +compiled expressions
        +year window
        +priorities
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
        +with_learned()
    }
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
    class ClusterApp {
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
    FolderContents --> TimestampedFile : scan yields
    Cluster --> TimestampedFile
    NamedCluster --|> Cluster : same files, plus number and name
    ClusterResult --> NamedCluster
    ClusterResult --> GapModel
    ClusterResult --> ClusterParams
    FolderModel --> GapModel
    GapModel --> ClusterParams : splits uses floor and ceiling
    ClusterApp --> ClusterResult
    ClusterApp --> TimelineView
    ClusterApp --> CalendarView
    TimelineView --> TimeScale
    CalendarView --> DayInfo
```

`NamedCluster` is not a subclass in code. It carries the same files plus the folder name. The diagram shows that as an extension of the data, not as inheritance.

`TimestampedFile.source` is empty when the file sits directly in the chosen folder. When the file already lives in an event folder, `source` is `event-folder/filename` and `name` stays the filename.

## Low-level design

### Preview

`ClusterApp.refresh` reads the option widgets into a `ClusterParams` and a `TimestampPatterns`, then calls `cluster_directory`. No file is moved.

```mermaid
sequenceDiagram
    participant App as ClusterApp
    participant Pipe as cluster_directory
    participant Model as model_file
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
        Parse-->>Pipe: timestamp or skip
    end
    Pipe->>Fit: timestamped files, params, saved model
    Fit->>Learn: log gaps strictly between floor and ceiling
    Learn-->>Fit: GapModel or none
    Fit-->>Pipe: clusters, learned boundary
    Pipe->>Model: save full-precision boundary
    Pipe-->>App: ClusterResult
    App->>App: draw timeline, calendar, lists
```

Inside `cluster_files` the steps are exactly those in [algorithm.md](algorithm.md): sort, form $g_i$, build $\mathcal{U}$, fit or reuse, then walk the gaps once.

Inside `parse_timestamp`, every enabled expression is tried. A match produces a candidate `(priority, start index, datetime)`. The highest priority wins. A tie keeps the earlier match in the name. A blank expression is off. A clock needs groups `y, mo, d, h, mi, s`. A day-month clock needs `a, b, y, h, mi`. An epoch needs `ms` and is converted with `datetime.fromtimestamp`. A date-only stamp is local midnight. Years outside the window are rejected.

`scan_directory` lists the chosen folder only one level down. A subdirectory whose name matches an event folder is opened, and only its immediate files are taken. Any other subdirectory is recorded and not entered. `filetimecluster-model.json` is never treated as a photo.

### Apply

Apply calls refresh first, so the confirmation dialog describes the clustering of the folder as it is now, including any files copied in since the last preview. After a successful move the drawing stays until another folder is chosen.

```mermaid
sequenceDiagram
    participant App as ClusterApp
    participant Move as move_into_cluster_folders
    participant Disk as Chosen folder

    App->>App: refresh
    App->>App: confirm
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
```

Folder names:

- one calendar day: `1 24-11-2015 10.01.25 to 18.50.08`
- several days: `2 09-11-2015 20.49.41 to 12-11-2015 10.24.42`

The leading number is the chronological index starting at 1, unpadded. The clock uses dots so the name is a legal folder name.

### Flatten

`flatten_cluster_folders` considers only immediate subfolders whose names match that pattern. It plans every move first. If any filename already exists in the chosen folder, nothing is moved. Otherwise each file is moved up and the event folder is removed when `rmdir` succeeds. A nested directory left inside an event folder keeps that folder on disk. Other subfolders are not touched. The model JSON stays, because it is not inside an event folder.

### A later batch

Copying files into the chosen folder does not start a background watcher. The next `refresh` (Choose folder, Update preview, or the refresh at the start of Apply) rebuilds one sequence:

1. Loose timestamped files in the chosen folder.
2. Timestamped files already inside event folders.

That sequence is fitted again. A new file joins an event when its neighbouring gaps do not split. It starts an event when they do. Apply then moves only the files whose current path is not already the destination, and drops event folders that became empty because their span, and therefore their name, changed.

## Descriptive write-up

The package splits along the three jobs the work actually has.

**Read a clock from a name.** `parse` is the only place a filename becomes a `datetime`. The expressions, the year window, and the priorities are data on `TimestampPatterns`, edited from the Options tab and compiled once per scan. Compilation fails closed: a bad expression or a missing named group raises `ValueError` with the field label, and the preview does not change.

**Decide the events.** `learn` is a pure function from a list of log-hours to a `GapModel` or `None`. `cluster` wraps that with the floor, the ceiling, the 36-hour fallback, and the reuse of a saved boundary. Neither module imports Tk or touches the filesystem. That is why the same function can cluster a camera roll held only in memory.

**Put the events on disk and on screen.** `organize` knows the folder-name grammar and the move rules. `pipeline` is the one function the window calls to go from a path to a `ClusterResult`, and it is also the function that writes the JSON. `ui` draws that result and asks before `organize` moves anything.

The window is one `ClusterApp` on one `tk.Tk`. The timeline and the calendar share cluster indices. Clicking a bar, a calendar day, or a row selects the same event. The timeline scale is in `layout.TimeScale`: one day is a constant number of pixels, so a gap on screen is the gap in time. Zoom changes that constant. The calendar colours a day by the event that owns it.

Options are not a second clustering mode. They are the inputs of the same functions: `ClusterParams.floor`, `ClusterParams.ceiling`, and the fields of `TimestampPatterns`. Restore defaults writes the built-in values back into the widgets and refreshes.

Failure stays local. An unreadable folder sets the status line. A move that would overwrite stops and reports `FileExistsError` or `OSError`. A model file that cannot be written is skipped; the preview still appears. A model file that is not valid JSON, or whose `learned` object is missing fields, loads as no saved boundary.

The icon shown by the window is `filenamecluster/src/filetimecluster/ui/assets/icon.svg`, rasterized to `icon.png` beside it because Tk’s `PhotoImage` loads the PNG.
