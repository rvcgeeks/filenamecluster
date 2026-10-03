"""Log path, line format, and tracing."""

import logging
import unittest
from pathlib import Path
from unittest.mock import patch

from filenamecluster import log as logmod
from filenamecluster.core import model_path


class LogTests(unittest.TestCase):
    def setUp(self):
        logmod.set_logging_enabled(False)

    def tearDown(self):
        logmod.set_logging_enabled(False)
        logmod._STATE["path"] = None
        logger = logging.getLogger("filenamecluster")
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
            handler.close()

    def test_each_operating_system_has_its_log_location(self):
        with (
            patch.object(logmod.sys, "platform", "darwin"),
            patch.object(logmod.Path, "home", return_value=Path("/Users/me")),
        ):
            self.assertEqual(
                logmod.log_path(),
                Path("/Users/me/Library/Logs/filenamecluster/filenamecluster.log"),
            )
        with (
            patch.object(logmod.sys, "platform", "win32"),
            patch.dict(logmod.os.environ, {"LOCALAPPDATA": "C:/Users/me/AppData/Local"}),
        ):
            self.assertEqual(
                logmod.log_path(),
                Path("C:/Users/me/AppData/Local/filenamecluster/Logs/filenamecluster.log"),
            )
        with (
            patch.object(logmod.sys, "platform", "win32"),
            patch.dict(logmod.os.environ, {"LOCALAPPDATA": ""}, clear=False),
            patch.object(logmod.Path, "home", return_value=Path("/Users/me")),
        ):
            self.assertEqual(
                logmod.log_path(),
                Path("/Users/me/AppData/Local/filenamecluster/Logs/filenamecluster.log"),
            )
        with (
            patch.object(logmod.sys, "platform", "linux"),
            patch.dict(logmod.os.environ, {"XDG_STATE_HOME": "/var/state"}),
        ):
            self.assertEqual(
                logmod.log_path(),
                Path("/var/state/filenamecluster/filenamecluster.log"),
            )
        with (
            patch.object(logmod.sys, "platform", "linux"),
            patch.dict(logmod.os.environ, {"XDG_STATE_HOME": ""}, clear=False),
            patch.object(logmod.Path, "home", return_value=Path("/home/me")),
        ):
            self.assertEqual(
                logmod.log_path(),
                Path("/home/me/.local/state/filenamecluster/filenamecluster.log"),
            )

    def test_traced_calls_record_pid_timestamp_and_exit(self):
        target = Path(self._tmp()) / "app.log"

        def sample(value: int) -> int:
            if value < 0:
                raise RuntimeError("no")
            return value + 1

        sample.__module__ = "filenamecluster.tests"
        wrapped = logmod.traced(sample)
        with patch.object(logmod, "log_path", return_value=target):
            logmod.set_logging_enabled(True)
            logmod.event("unit", path=target)
            logmod.detail("sample_step", value=1)
            logmod.log_call("filenamecluster.tests.sample")
            self.assertEqual(wrapped(1), 2)
            with self.assertRaises(RuntimeError):
                wrapped(-1)
            logmod.set_logging_enabled(False)
        text = target.read_text(encoding="utf-8")
        self.assertIn("EVENT logging_started", text)
        self.assertIn("EVENT unit", text)
        self.assertIn("DETAIL sample_step value=1", text)
        self.assertIn("CALL filenamecluster.tests.sample", text)
        self.assertIn("ENTER filenamecluster.tests.LogTests.test_traced_calls_record_pid_timestamp_and_exit.<locals>.sample", text)
        self.assertIn("EXIT filenamecluster.tests.LogTests.test_traced_calls_record_pid_timestamp_and_exit.<locals>.sample", text)
        self.assertIn("error=RuntimeError", text)
        line = next(row for row in text.splitlines() if "ENTER" in row)
        self.assertRegex(line, r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3} pid=\d+ INFO ")

    def test_the_switch_stops_new_lines_until_it_is_turned_on_again(self):
        target = Path(self._tmp()) / "app.log"
        with patch.object(logmod, "log_path", return_value=target):
            self.assertFalse(logmod.logging_enabled())
            logmod.event("hidden_before")
            logmod.set_logging_enabled(True)
            logmod.event("before")
            logmod.set_logging_enabled(False)
            logmod.event("hidden")
            logmod.detail("hidden_detail")
            logmod.set_logging_enabled(True)
            logmod.event("after")
            logmod.set_logging_enabled(False)
        text = target.read_text(encoding="utf-8")
        self.assertNotIn("hidden_before", text)
        self.assertIn("EVENT before", text)
        self.assertIn("EVENT logging_disabled", text)
        self.assertNotIn("EVENT hidden", text)
        self.assertNotIn("hidden_detail", text)
        self.assertIn("EVENT logging_enabled", text)
        self.assertIn("EVENT after", text)
        self.assertFalse(logmod.logging_enabled())

    def test_tracing_still_runs_when_the_log_cannot_be_opened(self):
        def sample() -> str:
            return "ok"

        sample.__module__ = "filenamecluster.tests"
        wrapped = logmod.traced(sample)
        with (
            patch.object(logmod, "log_path", return_value=Path("/no/such/dir/app.log")),
            patch.object(Path, "mkdir", side_effect=OSError("denied")),
        ):
            logmod.set_logging_enabled(True)
            self.assertEqual(wrapped(), "ok")
            logmod.set_logging_enabled(False)

    def test_module_functions_are_traced(self):
        self.assertTrue(getattr(model_path, "_filenamecluster_traced", False))

    def _tmp(self) -> str:
        from tempfile import mkdtemp

        folder = mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(folder, ignore_errors=True))
        return folder


if __name__ == "__main__":
    unittest.main()
