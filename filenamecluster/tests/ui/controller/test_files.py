"""Opening a file with the operating system's default application."""

import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from filenamecluster.ui.controller import SystemFiles


class OpenFileTests(unittest.TestCase):
    def test_each_platform_uses_its_default_opener(self):
        path = Path("photo.jpg")
        with (
            patch.object(sys, "platform", "darwin"),
            patch.object(subprocess, "Popen") as popen,
        ):
            SystemFiles().open_file(path)
        popen.assert_called_once_with(["open", "photo.jpg"])
        with (
            patch.object(sys, "platform", "win32"),
            patch.object(os, "startfile", create=True) as start,
        ):
            SystemFiles().open_file(path)
        start.assert_called_once_with("photo.jpg")
        with (
            patch.object(sys, "platform", "linux"),
            patch.object(subprocess, "Popen") as popen,
        ):
            SystemFiles().open_file(path)
        popen.assert_called_once_with(["xdg-open", "photo.jpg"])
