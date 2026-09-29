"""main: one build for this computer, with Windows Tcl and Mac app steps."""

import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from build import cli
from build.paths import MAC_APP
from build.tcl import MissingTclError, TclBundle


class CliCase(unittest.TestCase):
    def build(self, platform, argv=(), code=0, bundle=None):
        """Run ``main`` as if on ``platform``, with Nuitka and Tcl replaced."""

        out, err = io.StringIO(), io.StringIO()
        with (
            patch.object(cli.sys, "platform", platform),
            patch.object(cli.NuitkaBuild, "run", return_value=code) as run,
            patch.object(cli, "windows_bundle", side_effect=[bundle]) as tcl,
            patch.object(cli, "enable_retina") as retina,
            self.assertLogs("build", level="DEBUG") as logs,
            redirect_stdout(out),
            redirect_stderr(err),
        ):
            result = cli.main(list(argv))
        return result, run, tcl, retina, out.getvalue(), err.getvalue(), "\n".join(logs.output)


class CliTests(CliCase):
    def test_other_arguments_print_usage_and_do_not_build(self):
        result, run, _tcl, _retina, _out, err, logs = self.build("linux", ["--windows"])
        self.assertEqual(result, 2)
        self.assertIn("for this computer only", err)
        self.assertIn("python", logs)
        run.assert_not_called()

    def test_linux_builds_without_tcl_or_app_steps(self):
        result, run, tcl, retina, _out, _err, logs = self.build("linux", ["--no-cleanup"])
        self.assertEqual(result, 0)
        run.assert_called_once_with([])
        tcl.assert_not_called()
        retina.assert_not_called()
        self.assertIn("keep analysis True", logs)
        self.assertIn("intermediate files kept", logs)

    def test_mac_marks_the_app_high_resolution(self):
        result, _run, _tcl, retina, _out, _err, logs = self.build("darwin")
        self.assertEqual(result, 0)
        retina.assert_called_once_with(MAC_APP)
        self.assertIn("high resolution app", logs)

    def test_windows_packs_the_tcl_library(self):
        bundle = TclBundle(Path("tcl"), Path("tk"), (Path("registry1.3"),))
        result, run, tcl, _retina, _out, _err, logs = self.build("win32", bundle=bundle)
        self.assertEqual(result, 0)
        tcl.assert_called_once()
        run.assert_called_once_with(bundle.nuitka_options())
        self.assertIn("Tcl package registry1.3", logs)
        self.assertIn("--tcl-library-dir", logs)

    def test_windows_without_tcl_stops_before_nuitka(self):
        result, run, _tcl, _retina, _out, err, logs = self.build(
            "win32", bundle=MissingTclError("no Tcl")
        )
        self.assertEqual(result, 1)
        self.assertIn("no Tcl", err)
        self.assertIn("no Tcl", logs)
        run.assert_not_called()

    def test_a_failed_compile_returns_its_code_without_the_app_step(self):
        result, _run, _tcl, retina, _out, _err, logs = self.build("darwin", code=5)
        self.assertEqual(result, 5)
        self.assertIn("compile failed with exit 5", logs)
        retina.assert_not_called()
