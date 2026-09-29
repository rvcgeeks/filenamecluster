"""NuitkaBuild: one command per operating system."""

import unittest
from unittest.mock import MagicMock, patch

from build import nuitka
from build.nuitka import NuitkaBuild
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
        ):
            self.assertIn(option, command)
        for option in (
            "--verbose",
            "--show-scons",
            "--show-memory",
            "--show-modules",
            "--show-plugin-usage",
            "--show-progress",
        ):
            self.assertNotIn(option, command)
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

    def test_run_lets_nuitka_write_its_own_output_and_returns_the_code(self):
        completed = MagicMock()
        completed.returncode = 4
        build = NuitkaBuild("linux", python="py")
        with (
            patch.object(nuitka.subprocess, "run", return_value=completed) as run,
            self.assertLogs("build", level="DEBUG") as logs,
        ):
            self.assertEqual(build.run(["--x"]), 4)
        run.assert_called_once_with(build.command(["--x"]), cwd=ROOT, check=False)
        text = "\n".join(logs.output)
        self.assertIn("exit 4", text)
        self.assertNotIn("--verbose", text)
