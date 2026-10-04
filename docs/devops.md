# Making a release

Rajas Chavadekar (rvchavadekar@gmail.com)

A release is a numbered snapshot of the program, plus three files people can download. You pick the number, put a tag on that commit, and push the tag. GitHub Actions builds the program and puts the files on a Release page, each with its own download link.

Nothing is sent to PyPI. The downloadable files live only on the GitHub Release. User-visible changes for each version are recorded in [changelog.md](changelog.md); update it before tagging a release. A bug fix goes under that version’s **Fixed** section. For 0.1.6, **Added** records a progress bar on every folder read and file move, and a move-or-copy question when the input folder differs from storage. **Changed** records that Skip becomes **Delete from source** when the input folder is the storage folder. For 0.1.5, **Fixed** records that choosing a folder reads the event folders once, so the window does not stay on “Reading the saved options…”. **Added** records a required storage folder and an optional input folder. **Changed** records that a large folder does less repeated reading, and that Apply and Flatten prompts count down from `PROMPT_TIMEOUT_SECONDS` in `filenamecluster/src/filenamecluster/ui/view/prompt.py`, which is set to 30.

## The words

| Word | What it is |
|---|---|
| Version | The number in `filenamecluster/pyproject.toml`, such as `0.1.0`. |
| Tag | A name stuck to one commit. A release tag looks like `v0.1.0`: the letter `v`, then the same number. |
| GitHub Actions | The robot that builds the program on GitHub's computers. The instructions are `.github/workflows/release.yml`. |
| Workflow run | One time the robot did that work. You can open it and see each step. |
| Release | The page at [github.com/rvcgeeks/filenamecluster/releases](https://github.com/rvcgeeks/filenamecluster/releases). It lists the tag and the download links. |
| Artifact | A file kept on a workflow run. Handy for a test build. The public download is the Release, not the artifact. |

## Publish a version

Do this from the project root, on the `main` branch, after the tests pass.

1. Update `docs/changelog.md`, then set the version in `filenamecluster/pyproject.toml`:

   ```toml
   version = "0.1.2"
   ```

   Use three numbers: `major.minor.patch`. A fix or compatible feature release bumps the last number (`0.1.1` to `0.1.2`). A larger feature release bumps the middle number and sets the last back to zero (`0.2.0`). A breaking change bumps the first (`1.0.0`).

2. Commit that change and push `main`.

   ```bash
   git add docs/changelog.md filenamecluster/pyproject.toml filenamecluster/uv.lock
   git commit -m "Set version to 0.1.2."
   git push origin main
   ```

   Include any other files that belong in this version. The tag marks one commit, so that commit must already contain the version you want to ship.

3. Make the tag. The name is `v` plus the version, with no spaces.

   ```bash
   git tag v0.1.2
   git push origin v0.1.2
   ```

   Push that one tag by name. `git push --tags` also sends every other tag on your computer, including old ones you may not want on GitHub.

4. Open [Actions](https://github.com/rvcgeeks/filenamecluster/actions). A run named after the tag starts on its own. Wait until the three builds and **Publish release** are green.

5. Open the [Releases](https://github.com/rvcgeeks/filenamecluster/releases) page. The new release is titled `v0.1.2`. Under **Downloads**, each name is a link to the file itself.

For version `0.1.2` the links are:

- [filenamecluster-v0.1.2-windows.exe](https://github.com/rvcgeeks/filenamecluster/releases/download/v0.1.2/filenamecluster-v0.1.2-windows.exe) — the Windows program. Save it and open it.
- [filenamecluster-v0.1.2-macos.dmg](https://github.com/rvcgeeks/filenamecluster/releases/download/v0.1.2/filenamecluster-v0.1.2-macos.dmg) — a macOS disk image. Open it, then open `filenamecluster.app`.
- [filenamecluster-v0.1.2-linux](https://github.com/rvcgeeks/filenamecluster/releases/download/v0.1.2/filenamecluster-v0.1.2-linux) — the Linux program. In a terminal, `chmod +x` the file, then run it.

There is no zip around those files. The Windows and Linux downloads are the program. The macOS download is one disk image because a `.app` is a folder, and a Release can only hold a file. Opening the disk image shows `filenamecluster.app`.

The same three files are also listed as release assets under the notes. Either place downloads the same file.

## What the robot checks

On a tag, the first build step reads `version` in `filenamecluster/pyproject.toml` and compares it with the tag.

| Tag you pushed | Version in the file | Result |
|---|---|---|
| `v0.1.2` | `0.1.2` | The build runs. |
| `v0.1.2` | `0.1.0` | The build stops. Change the file, or delete this tag and use the tag that matches. |
| `0.1.2` or `version-0.1.2` | `0.1.2` | Actions ignores it. The tag must start with `v` and then the number. |

A manual run does not need a tag. It uses the version already in the file for the download name.

## What Actions does

The workflow file is `.github/workflows/release.yml`. It starts in two cases:

- You push a tag whose name matches `v*`, such as `v0.1.0` or `v1.2.3`.
- You start it by hand: Actions → **Release** → **Run workflow**. Choose the branch, usually `main`. A hand run builds the files and stores them on that run. It does not create a Release page.

### Build

Three jobs run at the same time, one per operating system: `ubuntu-latest`, `windows-latest`, and `macos-latest`. If one fails, the other two still finish. **Publish release** waits for all three, so a Release appears only when every build succeeded. Each job stops if it runs longer than 30 minutes.

Each build does this:

1. Checks out the commit the tag points at.
2. On a tag, checks that the tag is `v` plus the version in `pyproject.toml`.
3. Installs [uv](https://docs.astral.sh/uv/) and the locked dependencies from `filenamecluster/uv.lock`.
4. On Linux, installs the small libraries Tk needs to open a window.
5. Checks that Python can `import tkinter`.
6. Runs `uv run python -m build` in `filenamecluster/`. That uses Nuitka, which compiles for the host system, so each job builds only for the computer it is on. The compiled program includes the files under `ui/assets`.
   - Windows: one file, `dist/filenamecluster.exe`. It carries the Tcl and Tk library its window opens with, unpacked from the Python install, plus the registry and DDE packages. A Windows Python without that library stops the build.
   - Linux: one file, `dist/filenamecluster`
   - Mac: `dist/filenamecluster.app`. The app is a folder, which is what macOS expects.
7. Renames that program with the version. On a Mac it also wraps the app in a disk image, because the Release needs a single file.
8. Uploads that one file as an Actions artifact. The artifact name is the filename, for example `filenamecluster-v0.1.2-windows.exe`.

The build job is only allowed to read the repository. It cannot change the Release.

### Publish release

This job runs only for a tag. It runs on Linux after the three builds.

1. Downloads the three files from the build jobs.
2. Writes release notes. The notes are a **Downloads** list. Each item is a direct link:

   `https://github.com/rvcgeeks/filenamecluster/releases/download/v0.1.2/filenamecluster-v0.1.2-windows.exe`

   The last part of the link is the filename. Opening the link saves that file.

3. Creates the GitHub Release titled with the tag, or, if that release already exists, replaces the files and the notes.

This job is allowed to write repository contents, which is what creating a Release needs. It uses the token Actions already has. You do not add a password, and you do not add a PyPI token.

## Actions artifacts and the Release

Use the Release links when you want the program.

GitHub stores an Actions artifact as a zip. That is GitHub's rule for the **Artifacts** block on a workflow run. After this workflow, that zip contains the program file and nothing else. Unzip it once:

```text
filenamecluster-v0.1.2-windows.exe.zip
  filenamecluster-v0.1.2-windows.exe
```

The older runs were different. The workflow first put the app in its own zip, GitHub zipped that again, and the Windows zip held a `filenamecluster` folder with `filenamecluster.exe` and an `_internal` folder. Those extra layers are gone. The program is one file, and the Release link does not wrap it.

A hand-started run has artifacts only. Download them from the run page if you want to try a build without publishing.

## Looking after tags

See the tags on your computer:

```bash
git tag
```

See the commit a tag names:

```bash
git show v0.1.2 --no-patch
```

A tag name can be used once on GitHub until you delete it. Ship a new number (`v0.1.2`) when anyone should keep the files they already downloaded.

### Publish the same tag again

Use this when a Release for that tag already exists and you want to throw those files away and publish the same number from a chosen commit. The version in `filenamecluster/pyproject.toml` must still match the tag (`v0.1.2` needs `0.1.2`).

1. Delete the Release and the tag on GitHub. `--cleanup-tag` removes the remote tag as well as the Release page.

   ```bash
   gh release delete v0.1.2 --yes --cleanup-tag
   ```

   The same two deletions can be done by hand: on the release page, choose **Delete**, then remove the tag with `git push origin :refs/tags/v0.1.2`.

2. Delete the tag on your computer, then put it on the commit you want to ship.

   ```bash
   git tag -d v0.1.2
   git checkout main
   git pull origin main
   git tag v0.1.2
   ```

   Commit and push any fix to `main` before the `git tag` line. The tag sticks to the commit that is checked out.

3. Push that tag again.

   ```bash
   git push origin v0.1.2
   ```

   Actions starts a new run for `v0.1.2`. Wait until the three builds and **Publish release** are green. The Releases page shows `v0.1.2` again, with new download files.

If the tag was pushed and no Release page exists, skip `gh release delete`. Delete the tag locally and on GitHub, then tag and push as above:

```bash
git tag -d v0.1.2
git push origin :refs/tags/v0.1.2
```

If the build failed and the commit is already the one you want, open the failed run and choose **Re-run failed jobs**. That uses the same tag and the same commit. When a Release already exists, a successful re-run replaces its files and notes.

## A build that is not a release

Actions → **Release** → **Run workflow** → **Run workflow**.

The three programs are stored on that run for GitHub's artifact lifetime, 90 days unless the repository setting is different. Their names still include the version from `pyproject.toml`, such as `filenamecluster-v0.1.2-windows.exe`. No Release page is created, so there are no public download links until you push a matching tag.
