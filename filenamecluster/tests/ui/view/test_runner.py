"""DiskRunner spins and delivers work; AppModel owns the input lock."""

import threading
import time
from unittest.mock import patch

from filenamecluster.ui.controller import Wait
from filenamecluster.ui.view import SpinnerDialog, release_wait
from conftest import WindowCase


class RunnerTests(WindowCase):
    ALBUM = False
    LOAD = True

    def setUp(self):
        super().setUp()
        del self.app.view.run_work

    def run_visible(self, work):
        """Start ``work`` under the spinner and run the scheduled polls by hand."""

        view = self.app.view
        delivered, scheduled = [], []
        self.app.model.set_busy(True)

        def done(outcome):
            self.app.model.set_busy(False)
            delivered.append(outcome)

        with patch.object(SpinnerDialog, "__init__", return_value=None), \
                patch.object(SpinnerDialog, "close") as close, \
                patch.object(self.root, "after", side_effect=lambda _ms, fn: scheduled.append(fn)):
            view.run_work(Wait.OPEN, work, done)
            self.assertIn("disabled", view.apply_button.state())
            deadline = time.monotonic() + 5
            while not delivered and time.monotonic() < deadline:
                time.sleep(0.01)
                scheduled.pop(0)()
        close.assert_called_once_with()
        self.assertNotIn("disabled", view.apply_button.state())
        return delivered

    def test_work_runs_on_the_disk_thread_and_returns_its_value(self):
        names = []

        def work():
            names.append(threading.current_thread().name)
            return 42

        self.assertEqual(self.run_visible(work), [42])
        self.assertEqual(names, ["filenamecluster-disk"])

    def test_a_prompt_hides_the_spinner_before_the_prompt_returns(self):
        delivered = []
        scheduled = []

        def prompted(_outcome):
            release_wait(self.root)
            delivered.append(close.call_count)
            self.app.model.set_busy(False)

        self.app.model.set_busy(True)
        with patch.object(SpinnerDialog, "__init__", return_value=None), \
                patch.object(SpinnerDialog, "close") as close, \
                patch.object(self.root, "after", side_effect=lambda _ms, fn: scheduled.append(fn)):
            self.app.view.run_work(Wait.OPEN, lambda: None, prompted)
            deadline = time.monotonic() + 5
            while not delivered and time.monotonic() < deadline:
                time.sleep(0.01)
                scheduled.pop(0)()
        self.assertEqual(delivered, [1])
        self.assertGreaterEqual(close.call_count, 2)

    def test_an_exception_is_delivered_instead_of_raised(self):
        def work():
            raise OSError("disk gone")

        delivered = self.run_visible(work)
        self.assertIsInstance(delivered[0], OSError)
        self.assertEqual(str(delivered[0]), "disk gone")
