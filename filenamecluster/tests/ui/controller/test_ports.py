"""The controller and window match their explicit interaction ports."""

from filenamecluster.ui.controller import (
    DialogPort,
    DiskPort,
    FolderPickerPort,
    TaskRunnerPort,
)
from conftest import WindowCase


class PortTests(WindowCase):
    def test_the_window_and_the_disk_runner_match_the_ports(self):
        self.assertIsInstance(self.app.view, DialogPort)
        self.assertIsInstance(self.app.view, FolderPickerPort)
        self.assertIsInstance(self.app.view, TaskRunnerPort)
        self.assertIsInstance(self.app.controller._dispatch_disk, DiskPort)
