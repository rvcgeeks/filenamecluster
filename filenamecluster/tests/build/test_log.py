"""Build logs go to stderr at DEBUG, one handler for the whole run."""

import io
import unittest
from contextlib import redirect_stderr

from build.log import _StderrHandler, configure, get_logger


class LogTests(unittest.TestCase):
    def test_debug_lines_include_the_module_and_reach_stderr(self):
        logger = get_logger("build.logtest")
        err = io.StringIO()
        with redirect_stderr(err):
            logger.debug("staging %s", "folder")
            logger.info("built for %s", "linux")
        text = err.getvalue()
        self.assertIn("DEBUG build.logtest: staging folder", text)
        self.assertIn("INFO build.logtest: built for linux", text)

    def test_configure_keeps_a_single_stderr_handler(self):
        logger = configure()
        again = configure()
        self.assertIs(logger, again)
        handlers = [handler for handler in logger.handlers if isinstance(handler, _StderrHandler)]
        self.assertEqual(len(handlers), 1)
        self.assertEqual(logger.level, 10)
        self.assertFalse(logger.propagate)
