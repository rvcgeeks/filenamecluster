"""Opening a file with the operating system's default application."""

import unittest
from pathlib import Path
from unittest.mock import patch

from filenamecluster.ui.controller import files as file_ops

class OpenFileTests(unittest.TestCase):
    def test_each_platform_uses_its_default_opener(self):
        path = Path("photo.jpg")
        with (
            patch.object(file_ops.sys, "platform", "darwin"),
            patch.object(file_ops.subprocess, "Popen") as popen,
        ):
            file_ops.open_file(path)
        popen.assert_called_once_with(["open", "photo.jpg"])
        with (
            patch.object(file_ops.sys, "platform", "win32"),
            patch.object(file_ops.os, "startfile", create=True) as start,
        ):
            file_ops.open_file(path)
        start.assert_called_once_with("photo.jpg")
        with (
            patch.object(file_ops.sys, "platform", "linux"),
            patch.object(file_ops.subprocess, "Popen") as popen,
        ):
            file_ops.open_file(path)
        popen.assert_called_once_with(["xdg-open", "photo.jpg"])

