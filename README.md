# File Name Cluster

<p align="center">
  <img src="docs/assets/icon.png" alt="File Name Cluster" width="160">
</p>

Rajas Chavadekar (rvchavadekar@gmail.com) · [LinkedIn](https://www.linkedin.com/in/rvchavadekar)

File Name Cluster groups photos, videos, PDFs, and other timestamped files in one folder into events, using the date and time written in each filename. If a name has no timestamp, it reads only the capture time from a recognised picture or video container, or the CreationDate from a PDF. It learns the boundary between a short pause and a long pause from that folder alone, draws the events to scale, and moves each event into its own folder when you ask it to.

The metadata reader is implemented with the Python standard library. It supports JPEG, PNG, WebP, TIFF, HEIF/AVIF, MP4, MOV, M4V, 3GP, AVI, and PDF. It does not inspect pixels, GPS, camera details, document contents, or filesystem dates. A file with no usable filename or metadata capture time remains in place and appears under **Skipped**.

<p align="center">
  <img src="docs/assets/main-ui.png" alt="Clusters tab: timeline, calendar, event list, and day detail">
</p>

The Clusters tab. The timeline is the whole folder, to scale. The calendar colours each day by its event. The day detail is that day from 00:00 to 24:00.

## Documents

| | |
|---|---|
| This file | [README.md](README.md) |
| The mathematics | [algorithm.md](docs/algorithm.md) |
| Components, classes, HLD, LLD | [architecture.md](docs/architecture.md) |
| Releases and tags | [devops.md](docs/devops.md) |
| Version history | [changelog.md](docs/changelog.md) |

This readme is at the project root. `algorithm.md`, `architecture.md`, `devops.md`, and `changelog.md` live in `docs/`, beside `workspace` and `filenamecluster`.

## Run it

From `workspace`, with [uv](https://docs.astral.sh/uv/):

```bash
uv run filenamecluster
```

The interpreter is the uv-managed Python, which has Tk. Choose a folder in the window. The preview is drawn immediately. **Apply clustering** creates the event folders and moves the files. **Flatten clustering** moves those files back and removes the event folders. Other subfolders are left alone.

After Apply, the preview stays until you choose another folder. Copy a later batch into the same folder and click **Update preview**. Files already inside event folders are included. A new file joins an existing event when the pause is short enough, or starts a new one when it is not. Apply then moves only the files that need a different folder.

Double-click the selected orange or yellow event in the calendar, either timeline, or the cluster list to open its folder in a new file-manager window. The app explains when that folder has not been created yet. Double-click a file in **Day detail** to open it with the operating system's default application.

<p align="center">
  <img src="docs/assets/options.png" alt="Options tab: safety limits, year window, priorities, and filename patterns">
</p>

The Options tab keeps one arrangement. Filename patterns span the top. Under them, three columns hold the safety limits, the year window, and the learned model. The row sash and the two column sashes are resizable, and the panes stretch when the window does. The two safety limits wrap the learned boundary: never split before 3 hours, always split after 720 hours. The year window and priorities start with built-in values. Filename patterns are editable rows in a table with descriptions; additional rules can be added and custom rows can be removed. The model table is read-only and lists every field in `filenamecluster-model.json` (`learned.within_hours`, `learned.between_hours`, `learned.boundary_hours`, `learned.separated`) at the same precision as the file. Before a folder is chosen the values are blank; when the folder has no fitted boundary they read `null`. **Update preview** redraws with the current values and refreshes the model table. **Restore defaults** puts the built-in values back.

## What gets written

In the folder you chose, next to the files, not hidden:

```json
{
  "learned": {
    "within_hours": 17.55637365032029,
    "between_hours": 81.12551521324934,
    "boundary_hours": 37.98317023002044,
    "separated": true
  }
}
```

`filenamecluster-model.json` keeps the fitted hours at full precision. The Options tab lists these fields in a read-only table with the same digits. A later batch that is too small to fit a new boundary reuses these numbers. The scan ignores this filename, so it is not treated as media.

Event folders are named so a plain sort follows time:

```text
1 24-11-2015 10.01.25 to 18.50.08
2 09-11-2015 20.49.41 to 12-11-2015 10.24.42
```

## Layout

```text
filenamecluster/
  README.md             this introduction
  docs/                 algorithm, architecture, changelog, devops, assets
  filenamecluster/      the package and the Tk app
  workspace/            uv project that runs the app; data/ and filenames.txt
```

`workspace` installs `filenamecluster` from the sibling directory. `uv run stub create filenames.txt` builds empty stand-in files in `workspace/data` from a `dir` listing, `ls -l` output, or one name per line. `uv run stub clean` deletes empty files there, then empty folders, and leaves anything that still has content.

## Tests

From `filenamecluster`:

```bash
uv run pytest
```

Coverage is written to `filenamecluster/reports/` and is required to stay at or above 80%. UI tests build real Tk widgets on a root that remains withdrawn, so the suite never presents an application window.
