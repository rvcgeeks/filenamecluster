"""NuitkaBuild: one command per operating system."""

import io
import unittest
from unittest.mock import MagicMock, patch

from build import nuitka
from build.nuitka import VERBOSE, NuitkaBuild
from build.paths import ASSETS, PACKAGE, ROOT


class NuitkaCommandTests(unittest.TestCase):
    def test_every_build_is_standalone_with_tk_and_the_assets(self):
        command = NuitkaBuild("linux", python="py").command()
        self.assertEqual(command[:3], ["py", "-m", "nuitka"])
        for option in (
            "--standalone",
            "--enable-plugins=tk-inter",
            "--output-dir=dist",
            f"--include-data-dir={ASSETS}=filenamecluster/ui/assets",
            "--remove-output",
            *VERBOSE,
        ):
            self.assertIn(option, command)
        self.assertEqual(command[-2:], ["--python-flag=-m", str(PACKAGE)])

    def test_linux_and_windows_write_one_file(self):
        linux = NuitkaBuild("linux").command()
        windows = NuitkaBuild("win32").command()
        for command in (linux, windows):
            self.assertIn("--onefile", command)
            self.assertIn("--output-filename=filenamecluster", command)
            self.assertNotIn("--macos-create-app-bundle", command)
        self.assertIn("--windows-console-mode=disable", windows)
        self.assertNotIn("--windows-console-mode=disable", linux)

    def test_mac_writes_an_app_bundle(self):
        command = NuitkaBuild("darwin").command()
        self.assertIn("--macos-create-app-bundle", command)
        self.assertIn(f"--macos-app-icon={ASSETS / 'icon.png'}", command)
        self.assertIn("--output-folder-name=filenamecluster", command)
        self.assertNotIn("--onefile", command)

    def test_keeping_analysis_leaves_the_intermediate_files(self):
        self.assertNotIn("--remove-output", NuitkaBuild("linux", keep_analysis=True).command())

    def test_extra_options_come_before_the_package(self):
        command = NuitkaBuild("win32").command(["--tcl-library-dir=x"])
        self.assertLess(command.index("--tcl-library-dir=x"), command.index("--python-flag=-m"))

    def test_run_logs_every_nuitka_line_and_returns_the_code(self):
        process = MagicMock()
        process.stdout = io.StringIO("Nuitka: compiling\n")
        process.wait.return_value = 4
        build = NuitkaBuild("linux", python="py")
        with (
            patch.object(nuitka.subprocess, "Popen", return_value=process) as popen,
            self.assertLogs("build", level="DEBUG") as logs,
        ):
            self.assertEqual(build.run(["--x"]), 4)
        popen.assert_called_once_with(
            build.command(["--x"]),
            cwd=ROOT,
            stdout=nuitka.subprocess.PIPE,
            stderr=nuitka.subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        text = "\n".join(logs.output)
        self.assertIn("--verbose", text)
        self.assertIn("Nuitka: compiling", text)
        self.assertIn("exit 4", text)
