"""A real window on a Tk root that is never mapped onto the screen, shared by the UI tests."""

import tkinter as tk
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from filenamecluster.log import set_logging_enabled
from filenamecluster.ui.app import FileNameClusterApp
from filenamecluster.ui.view import use_script

PHOTOS = (
    "IMG_20240101_100000.jpg",
    "IMG_20240101_110000.jpg",
    "IMG_20240102_090000.jpg",
    "IMG_20240120_080000.jpg",
    "notes.txt",
)


def make_root() -> tk.Tk:
    """A Tk interpreter whose window stays withdrawn for the whole test.

    Creating ``Tk`` can map a window before Python runs the next line, so this
    withdraws it immediately and ignores later requests to show, zoom, or fill
    the screen. Tests still build the real widgets. They do not present them.
    """

    try:
        root = tk.Tk()
    except tk.TclError as exc:
        raise unittest.SkipTest(f"no display for Tk: {exc}")
    root.withdraw()
    real_attributes = root.attributes
    real_state = root.state

    def attributes(*args):
        if len(args) >= 2 and args[0] == "-fullscreen" and args[1]:
            return ""
        return real_attributes(*args)

    def state(value=None):
        if value is None:
            return real_state()
        if value != "withdrawn":
            return real_state()
        return real_state(value)

    root.attributes = attributes
    root.state = state
    root.deiconify = lambda: None
    root.withdraw()
    return root


def run_inline(_message_key, work, on_done) -> None:
    """Run disk work on this thread. Window tests pass this instead of the spinner."""

    try:
        outcome = work()
    except Exception as exc:
        outcome = exc
    on_done(outcome)


class WindowCase(unittest.TestCase):
    """``self.app`` on a withdrawn root, and ``self.folder`` holding ``PHOTOS``.

    ``ALBUM`` adds an ordinary subfolder. ``LOAD`` previews the folder in ``setUp``.
    """

    ALBUM = True
    LOAD = False

    def setUp(self):
        set_logging_enabled(False)
        self.tmp = TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        for name in PHOTOS:
            (self.folder / name).write_bytes(b"x")
        if self.ALBUM:
            (self.folder / "album").mkdir()
        self.root = make_root()
        self.app = FileNameClusterApp(self.root)
        self.app.view.run_work = run_inline
        if self.LOAD:
            self.app.controller.load_folder(self.folder)
        self.root.update_idletasks()

    def tearDown(self):
        set_logging_enabled(False)
        use_script(self.root, self.app.view.fonts, "en")
        self.assertEqual(self.root.state(), "withdrawn")
        self.root.destroy()
        self.tmp.cleanup()


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    """The core package is required to be fully covered. The rest of the suite stays at 80%."""

    if session.config.getoption("no_cov", default=False):
        return
    plugin = session.config.pluginmanager.getplugin("_cov")
    cov = getattr(plugin, "cov", None)
    if cov is None:
        return
    root = Path(__file__).resolve().parents[1] / "src" / "filenamecluster" / "core"
    measured = {Path(name).resolve(): name for name in cov.get_data().measured_files()}
    gaps: list[str] = []
    for source in sorted(root.rglob("*.py")):
        filename = measured.get(source.resolve())
        if filename is None:
            gaps.append(f"{source.relative_to(root)} was not imported")
            continue
        _name, _statements, _excluded, missing, _text = cov.analysis2(filename)
        if missing:
            gaps.append(f"{source.relative_to(root)} missing {missing}")
    if not gaps or session.exitstatus or exitstatus:
        return
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    reporter.write_line("core coverage is below 100%:")
    for gap in gaps:
        reporter.write_line(f"  {gap}")
    session.exitstatus = 1
