"""The Tcl and Tk library a Windows program opens its window with."""

import io
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

from build.tcl import (
    MissingTclError,
    PythonInstall,
    TclBundle,
    unpack_library,
    windows_bundle,
)

TCL_FILES = {
    "tcl_library/init.tcl": "# init\n",
    "tcl_library/clock.tcl": "package require registry 1.3\n",
    "tcl_library/encoding/cp1252.enc": "cp1252\n",
    "tcl_library/tzdata/Asia/Kolkata": "zone\n",
}
TK_FILES = {
    "tk_library/dialog.tcl": "# dialog\n",
    "tk_library/tk.tcl": "# tk\n",
    "tk_library/ttk/ttk.tcl": "# ttk\n",
}


def dll_with_zip(path: Path, files: dict[str, str]) -> None:
    """A stand-in for ``tcl90.dll``: machine code followed by a zip."""

    packed = io.BytesIO()
    with zipfile.ZipFile(packed, "w") as archive:
        for name, text in files.items():
            archive.writestr(name, text)
    path.write_bytes(b"MZ" + b"\0" * 512 + packed.getvalue())


def windows_python(root: Path) -> Path:
    """The Windows Python 3.14 layout: scripts in DLLs, packages under ``tcl``."""

    dlls = root / "DLLs"
    dlls.mkdir(parents=True)
    dll_with_zip(dlls / "tcl90.dll", TCL_FILES)
    dll_with_zip(dlls / "tcl9tk90.dll", TK_FILES)
    (dlls / "zlib1.dll").write_bytes(b"MZ not a zip")
    tk = root / "tcl" / "tk9.0"
    tk.mkdir(parents=True)
    (tk / "pkgIndex.tcl").write_text("package ifneeded Tk 9.0 {}\n")
    for name, dll in (("registry1.3", "tcl9registry13.dll"), ("dde1.4", "tcl9dde14.dll")):
        package = root / "tcl" / name
        package.mkdir()
        (package / "pkgIndex.tcl").write_text("package ifneeded x 1 {}\n")
        (package / dll).write_bytes(b"MZ")
    return root


class TclCase(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        self.staging = self.folder / "staging"
        self.staging.mkdir()

    def tearDown(self):
        self.tmp.cleanup()


class BundleTests(TclCase):
    def test_dll_libraries_are_unpacked_with_encodings_and_time_zones(self):
        install = PythonInstall((windows_python(self.folder / "python"),))
        bundle = windows_bundle(self.staging, install, "9.0")
        self.assertEqual(bundle.tcl, self.staging / "tcl")
        self.assertEqual(bundle.tk, self.staging / "tk")
        for relative in ("init.tcl", "clock.tcl", "encoding/cp1252.enc", "tzdata/Asia/Kolkata"):
            self.assertTrue((bundle.tcl / relative).is_file(), relative)
        for relative in ("dialog.tcl", "tk.tcl", "ttk/ttk.tcl"):
            self.assertTrue((bundle.tk / relative).is_file(), relative)
        self.assertEqual([package.name for package in bundle.packages], ["dde1.4", "registry1.3"])

    def test_a_library_folder_on_disk_is_used_as_it_is(self):
        root = windows_python(self.folder / "python")
        for name, marker in (("tcl8.6", "init.tcl"), ("tk8.6", "dialog.tcl")):
            (root / "tcl" / name).mkdir()
            (root / "tcl" / name / marker).write_text("# on disk\n")
        bundle = windows_bundle(self.staging, PythonInstall((root,)), "8.6")
        self.assertEqual(bundle.tcl, root / "tcl" / "tcl8.6")
        self.assertEqual(bundle.tk, root / "tcl" / "tk8.6")
        self.assertFalse((self.staging / "tcl").exists())

    def test_a_python_without_the_library_stops_the_build(self):
        (self.folder / "empty" / "DLLs").mkdir(parents=True)
        with self.assertRaises(MissingTclError) as stop:
            windows_bundle(self.staging, PythonInstall((self.folder / "empty",)), "9.0")
        self.assertIn("Tcl init.tcl and Tk dialog.tcl", str(stop.exception))

    def test_options_copy_the_libraries_and_packages_into_the_program(self):
        package = Path("C:/py/tcl/registry1.3")
        bundle = TclBundle(Path("C:/t/tcl"), Path("C:/t/tk"), (package,))
        self.assertEqual(
            bundle.nuitka_options(),
            [
                f"--tcl-library-dir={Path('C:/t/tcl')}",
                f"--tk-library-dir={Path('C:/t/tk')}",
                f"--include-data-dir={package}=registry1.3",
            ],
        )


class UnpackTests(TclCase):
    def test_a_plain_zip_unpacks_below_its_library_folder(self):
        archive = self.folder / "libtcl9.0.4.zip"
        with zipfile.ZipFile(archive, "w") as packed:
            for name, text in TCL_FILES.items():
                packed.writestr(name, text)
            packed.writestr("../escape.tcl", "no")
        dest = self.staging / "tcl"
        self.assertEqual(unpack_library(archive, "init.tcl", dest), dest)
        self.assertTrue((dest / "encoding" / "cp1252.enc").is_file())
        self.assertFalse((self.staging / "escape.tcl").exists())

    def test_archives_without_the_marker_are_skipped(self):
        archive = self.folder / "tk.dll"
        dll_with_zip(archive, TK_FILES)
        not_zip = self.folder / "zlib1.dll"
        not_zip.write_bytes(b"MZ")
        self.assertIsNone(unpack_library(archive, "init.tcl", self.staging / "a"))
        self.assertIsNone(unpack_library(not_zip, "init.tcl", self.staging / "b"))
        self.assertFalse((self.staging / "a").exists())


class PythonInstallTests(TclCase):
    def test_a_venv_adds_the_base_python_it_names(self):
        base = self.folder / "base"
        base.mkdir()
        venv = self.folder / "venv"
        venv.mkdir()
        (venv / "pyvenv.cfg").write_text(
            f"home = {base}\nincludes = false\nexecutable = {base / 'python.exe'}\n",
            encoding="utf-8",
        )
        install = PythonInstall.from_prefixes([venv, venv])
        self.assertEqual(install.roots, (venv.resolve(), base.resolve()))

    def test_current_python_includes_its_own_prefix(self):
        import sys

        self.assertIn(Path(sys.base_prefix).resolve(), PythonInstall.current().roots)
