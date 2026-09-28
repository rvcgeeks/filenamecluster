"""Create empty stand-in files from a listing, or remove empty ones.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Introduction: ``readme.md``. Mathematics: ``docs/algorithm.md``.
Design: ``docs/architecture.md``.

Run from the workspace project so uv supplies the interpreter::

    uv run stub create filenames.txt
    uv run stub clean

The listing may be a Windows ``dir`` dump, ``ls -l`` output, or one filename
per line. A relative listing path is resolved from the directory that holds
``pyproject.toml``, beside the ``data`` folder. Files are created in ``data``.
``clean`` deletes empty files there and then empty folders, and leaves
anything that still has content.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

def _project_root() -> Path:
    """Directory that contains this project's ``pyproject.toml``."""

    for folder in Path(__file__).resolve().parents:
        if (folder / "pyproject.toml").is_file():
            return folder
    return Path(__file__).resolve().parents[1]


PROJECT = _project_root()
DATA = PROJECT / "data"
PROTECTED = {"stub.py", "filenames.txt"}

_DIR_ENTRY = re.compile(
    r"^(?P<date>\d{2}-\d{2}-\d{4})\s+"
    r"(?P<time>\d{2}:\d{2})\s+"
    r"(?P<kind><DIR>|[\d,]+)\s+"
    r"(?P<name>.*\S)\s*$"
)
_LS_ENTRY = re.compile(
    r"^(?P<type>[bcdlps-])[\w-]{9}[@+.]?\s+"
    r"\d+\s+\S+\s+\S+\s+\d+\s+"
    r"(?:"
    r"[A-Za-z]{3}\s+\d{1,2}\s+(?:\d{2}:\d{2}|\d{4})"
    r"|"
    r"\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}"
    r")\s+"
    r"(?P<name>.+)$"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="stub",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Create empty stand-in files in data/ from a filename listing, "
            "or delete empty files and folders there."
        ),
        epilog=(
            "examples:\n"
            "  uv run stub create filenames.txt\n"
            "  uv run stub clean\n"
            "\n"
            "filenames.txt sits beside pyproject.toml, next to the data folder.\n"
            "A relative listing path is resolved from that project directory."
        ),
    )
    commands = parser.add_subparsers(dest="command", required=True, metavar="command")

    create = commands.add_parser(
        "create",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help="make an empty file in data for every file named in the listing",
        description=(
            "Read a listing and create an empty file in data/ for each name. "
            "Directories in a dir or ls -l listing are skipped. "
            "Files that already exist are left unchanged."
        ),
        epilog=(
            "The listing may be a Windows dir dump, ls -l output, or one\n"
            "filename per line. Example:\n"
            "  uv run stub create filenames.txt"
        ),
    )
    create.add_argument(
        "listing",
        help="path relative to pyproject.toml, or an absolute path",
    )
    commands.add_parser(
        "clean",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help="delete empty files and empty folders; keep anything with content",
        description=(
            "Under data/, delete files whose size is 0, then delete folders "
            "that are empty after that. A file with any content is kept, and "
            "so is any folder that still holds one."
        ),
        epilog="Example:\n  uv run stub clean",
    )

    args = parser.parse_args(argv)
    if args.command == "create":
        create_files(args.listing)
    else:
        clean_empty()
    return 0


def create_files(
    listing: str,
    root: Path | None = None,
    project: Path | None = None,
) -> None:
    folder = root or DATA
    path = _listing_path(listing, project or PROJECT)
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    names, ignored_dirs, mode = _names_from_listing(lines)

    created = present = skipped = 0
    for raw in names:
        name = _plain_name(raw)
        if name is None:
            skipped += 1
            continue
        target = folder / name
        if target.exists():
            present += 1
            continue
        target.touch()
        created += 1

    print(
        f"{mode}: created {created}, already present {present}, "
        f"directories ignored {ignored_dirs}, skipped {skipped}"
    )


def clean_empty(root: Path | None = None) -> None:
    folder_root = root or DATA
    removed_files = 0
    removed_dirs = 0
    for dirpath, _dirnames, filenames in os.walk(folder_root, topdown=False):
        folder = Path(dirpath)
        for filename in filenames:
            file = folder / filename
            if filename in PROTECTED or not file.is_file():
                continue
            if file.stat().st_size == 0:
                file.unlink()
                removed_files += 1
        if folder != folder_root and _is_empty_dir(folder):
            folder.rmdir()
            removed_dirs += 1
    print(f"removed {removed_files} empty files and {removed_dirs} empty folders")


def _listing_path(listing: str, project: Path) -> Path:
    path = Path(listing)
    if not path.is_absolute():
        path = project / path
    if path.is_file():
        return path
    raise SystemExit(f"listing not found: {listing}")


def _names_from_listing(lines: list[str]) -> tuple[list[str], int, str]:
    dir_hits = [match for line in lines if (match := _DIR_ENTRY.match(line))]
    ls_hits = [match for line in lines if (match := _LS_ENTRY.match(line))]

    names: list[str] = []
    ignored_dirs = 0
    if dir_hits:
        for match in dir_hits:
            if match.group("kind") == "<DIR>":
                ignored_dirs += 1
            else:
                names.append(match.group("name"))
        return names, ignored_dirs, "dir"

    if ls_hits:
        for match in ls_hits:
            kind = match.group("type")
            name = match.group("name")
            if kind == "d":
                ignored_dirs += 1
                continue
            if kind == "l" and " -> " in name:
                name = name.split(" -> ", 1)[0]
            if kind not in "-l":
                continue
            names.append(name)
        return names, ignored_dirs, "ls -l"

    for line in lines:
        name = line.rstrip("\r\n")
        if not name.strip() or name in {".", ".."}:
            continue
        names.append(name)
    return names, 0, "names"


def _plain_name(raw: str) -> str | None:
    name = raw[2:] if raw.startswith(("./", ".\\")) else raw
    if (
        not name
        or name in PROTECTED
        or name in {".", ".."}
        or "/" in name
        or "\\" in name
    ):
        return None
    return name


def _is_empty_dir(folder: Path) -> bool:
    try:
        next(folder.iterdir())
    except StopIteration:
        return True
    return False


if __name__ == "__main__":
    sys.exit(main())
