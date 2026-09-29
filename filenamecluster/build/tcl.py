"""The Tcl and Tk library the Windows program opens its window with.

Tcl 8.6 keeps ``init.tcl`` in a ``tcl8.6`` folder. Windows Python 3.14 stores
the Tcl library, including encodings and time-zone data, inside
``tcl90.dll``, and the Tk library inside ``tcl9tk90.dll``. Those libraries are
unpacked into ordinary folders. Nuitka copies the folders into the program and
points the window at them when the program runs. The registry and DDE packages
are copied beside that library, which is where Windows Tcl looks for them.
"""

from __future__ import annotations

import shutil
import sys
import zipfile
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from build.log import get_logger

log = get_logger(__name__)

LIBRARY_FOLDERS = (Path("tcl"), Path("lib"), Path("Lib"), Path("Library") / "lib")
ARCHIVE_FOLDERS = ("tcl", "DLLs", "lib", "Lib")


class MissingTclError(RuntimeError):
    """This Python has no Tcl or Tk library a window could open with."""


@dataclass(frozen=True)
class TclBundle:
    """Library folders and Windows packages to copy into the program."""

    tcl: Path
    tk: Path
    packages: tuple[Path, ...] = ()

    def nuitka_options(self) -> list[str]:
        options = [f"--tcl-library-dir={self.tcl}", f"--tk-library-dir={self.tk}"]
        options.extend(
            f"--include-data-dir={package}={package.name}" for package in self.packages
        )
        return options


@dataclass(frozen=True)
class PythonInstall:
    """The folders of one Python install that may hold its Tcl files."""

    roots: tuple[Path, ...]

    @classmethod
    def current(cls) -> PythonInstall:
        prefixes = (
            sys.base_prefix,
            getattr(sys, "base_exec_prefix", sys.base_prefix),
            sys.prefix,
            sys.exec_prefix,
        )
        return cls.from_prefixes(Path(prefix) for prefix in prefixes)

    @classmethod
    def from_prefixes(cls, prefixes: Iterable[Path]) -> PythonInstall:
        """Each prefix, and the base Python a ``pyvenv.cfg`` in it names."""

        candidates: list[Path] = []
        for prefix in prefixes:
            log.debug("prefix %s", prefix)
            candidates.append(prefix)
            for home in _venv_homes(prefix / "pyvenv.cfg"):
                log.debug("pyvenv.cfg %s names %s", prefix / "pyvenv.cfg", home)
                candidates.append(home)
        roots: list[Path] = []
        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved not in roots:
                roots.append(resolved)
        log.debug("install roots %s", [str(root) for root in roots])
        return cls(tuple(roots))

    def library(self, folder_name: str, marker: str, staging: Path) -> Path | None:
        """A folder whose top level holds ``marker``, such as ``init.tcl``.

        A folder already on disk is used as it is. Otherwise the library is
        unpacked into ``staging`` from a zip, or from a DLL carrying that zip.
        """

        log.debug("looking for %s in %s, else unpack to %s", marker, folder_name, staging)
        for root in self.roots:
            for relative in LIBRARY_FOLDERS:
                directory = root / relative / folder_name
                found = (directory / marker).is_file()
                log.debug("folder %s marker %s", directory, found)
                if found:
                    return directory
        for archive in self._archives():
            log.debug("archive %s size %s", archive, archive.stat().st_size)
            if unpack_library(archive, marker, staging) is not None:
                log.debug("unpacked %s from %s", marker, archive)
                return staging
        log.debug("no %s", marker)
        return None

    def windows_packages(self) -> tuple[Path, ...]:
        """Folders under ``tcl`` that load a DLL, such as ``registry1.3``."""

        packages: list[Path] = []
        names: set[str] = set()
        for root in self.roots:
            folder = root / "tcl"
            if not folder.is_dir():
                log.debug("no package folder %s", folder)
                continue
            for path in sorted(folder.iterdir()):
                if path.name in names or not _is_dll_package(path):
                    log.debug("skip package %s", path)
                    continue
                log.debug("windows package %s", path)
                names.add(path.name)
                packages.append(path)
        return tuple(packages)

    def _archives(self) -> Iterable[Path]:
        for root in self.roots:
            for name in ARCHIVE_FOLDERS:
                folder = root / name
                if not folder.is_dir():
                    log.debug("no archive folder %s", folder)
                    continue
                for path in sorted(folder.iterdir()):
                    if path.suffix.lower() in {".zip", ".dll"} and path.is_file():
                        yield path


def unpack_library(archive: Path, marker: str, dest: Path) -> Path | None:
    """Unpack the library holding ``marker`` from ``archive`` into ``dest``."""

    if dest.exists():
        log.debug("staging %s already exists", dest)
        return None
    if not zipfile.is_zipfile(archive):
        log.debug("%s is not a zip", archive)
        return None
    with zipfile.ZipFile(archive) as packed:
        names = [name for name in packed.namelist() if not name.endswith("/")]
        log.debug("%s has %s files", archive.name, len(names))
        matches = [name for name in names if name == marker or name.endswith("/" + marker)]
        if not matches:
            log.debug("%s has no %s", archive.name, marker)
            return None
        prefix = min(matches, key=len)[: -len(marker)]
        log.debug("unpack prefix %r marker %s into %s", prefix, marker, dest)
        written = 0
        for name in names:
            if not name.startswith(prefix):
                log.debug("skip %s outside prefix", name)
                continue
            relative = Path(name[len(prefix) :])
            if not relative.parts or ".." in relative.parts:
                log.debug("skip unsafe path %s", name)
                continue
            target = dest.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            data = packed.read(name)
            target.write_bytes(data)
            written += 1
            log.debug("wrote %s (%s bytes)", relative, len(data))
    if not (dest / marker).is_file():
        log.debug("unpack of %s left no %s", archive.name, marker)
        shutil.rmtree(dest, ignore_errors=True)
        return None
    log.debug("unpacked %s files from %s", written, archive.name)
    return dest


def windows_bundle(
    staging: Path,
    install: PythonInstall | None = None,
    version: str | None = None,
) -> TclBundle:
    """The library this Windows Python opens a window with.

    Raises ``MissingTclError`` so the build stops before it writes a program
    whose window cannot open.
    """

    log.debug("windows bundle staging %s", staging)
    if install is None:
        install = PythonInstall.current()
    if version is None:
        import tkinter

        version = str(tkinter.TkVersion)
        log.debug("TkVersion %s", version)
    log.debug("tcl version folder tcl%s", version)
    tcl = install.library(f"tcl{version}", "init.tcl", staging / "tcl")
    tk = install.library(f"tk{version}", "dialog.tcl", staging / "tk")
    missing = [
        label for label, found in (("Tcl init.tcl", tcl), ("Tk dialog.tcl", tk)) if found is None
    ]
    if missing:
        raise MissingTclError(
            f"This Windows Python has no {' and '.join(missing)} the program can open a window with.\n"
            "The build stops so it does not write a program whose window cannot open."
        )
    assert tcl is not None and tk is not None
    return TclBundle(tcl, tk, install.windows_packages())


def _venv_homes(cfg: Path) -> Sequence[Path]:
    if not cfg.is_file():
        return ()
    homes: list[Path] = []
    for line in cfg.read_text(encoding="utf-8").splitlines():
        key, separator, raw = line.partition("=")
        key = key.strip()
        raw = raw.strip().strip('"')
        if separator != "=" or key not in {"home", "executable"} or not raw:
            continue
        path = Path(raw)
        homes.append(path.parent if key == "executable" else path)
    return homes


def _is_dll_package(path: Path) -> bool:
    if not path.is_dir() or not (path / "pkgIndex.tcl").is_file():
        return False
    return any(child.suffix.lower() == ".dll" for child in path.iterdir())
