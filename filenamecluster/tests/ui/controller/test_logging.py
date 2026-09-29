"""SystemLogging applies the session value to the logging service."""

import unittest
from unittest.mock import patch

from filenamecluster.log import logging_enabled, set_logging_enabled
from filenamecluster.ui.controller import SystemLogging


class LoggingPortTests(unittest.TestCase):
    def tearDown(self):
        set_logging_enabled(False)

    def test_apply_uses_the_value_the_model_already_stored(self):
        with patch("filenamecluster.ui.controller.logging.set_logging_enabled") as apply:
            SystemLogging().apply(True)
        apply.assert_called_once_with(True)
        self.assertFalse(logging_enabled())
