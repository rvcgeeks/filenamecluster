"""The wait overlay plays spinner.gif at its own speed and stays off screen in tests."""

import tempfile
import tkinter as tk
import unittest
from pathlib import Path

from filenamecluster.ui.view import SpinnerDialog, gif_delays, gif_frames, spinner_path


def _advance_frame(dialog: SpinnerDialog) -> None:
    """Run the next GIF tick without ``Tk.update``.

    ``update`` drains the macOS event queue. A reopen Apple event during that
    drain bus-errors inside Tcl (``Tcl_FindCommand``).
    """

    job = dialog._job
    if job is None:
        raise AssertionError("spinner did not schedule the next frame")
    script = dialog.top.tk.call("after", "info", job)
    command = script[0] if isinstance(script, tuple) else script
    dialog.top.tk.call(command)
    # The timer is still armed. Cancel it after the callback: cancelling
    # first deletes the Tcl command, and Tk 9 reports that command as
    # ``name timer``, where ``timer`` is not an argument.
    try:
        dialog.top.after_cancel(job)
    except tk.TclError:
        pass


class SpinnerTests(unittest.TestCase):
    def test_gif_delays_follow_the_file(self):
        frames_in_file = len(gif_delays(spinner_path()))
        self.assertGreaterEqual(frames_in_file, 2)
        self.assertLessEqual(max(gif_delays(spinner_path())), 60)
        with tempfile.TemporaryDirectory() as tmp:
            broken = Path(tmp) / "broken.gif"
            broken.write_bytes(b"not a gif")
            self.assertEqual(gif_delays(broken), [])
            self.assertEqual(gif_delays(Path(tmp) / "missing.gif"), [])

    def test_spinner_gif_animates_and_closes(self):
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            raise unittest.SkipTest(f"no display for Tk: {exc}") from exc
        root.withdraw()
        try:
            frames = gif_frames(spinner_path())
            self.assertGreaterEqual(len(frames), 2)
            self.assertEqual(len(frames), len(gif_delays(spinner_path())))
            dialog = SpinnerDialog(root, "Moving files into event folders…")
            self.assertEqual(len(dialog.frames), len(frames))
            self.assertEqual(dialog.index, 1)
            self.assertEqual(str(dialog.top.state()), "withdrawn")
            self.assertEqual(dialog.font.actual("weight"), "bold")
            self.assertEqual(
                dialog.canvas.itemcget(dialog.text_id, "text"),
                "Moving files into event folders…",
            )
            if str(root.tk.call("tk", "windowingsystem")) == "aqua":
                self.assertEqual(dialog.top.attributes("-transparent"), 1)
                self.assertEqual(str(dialog.top.cget("background")), "systemTransparent")
                self.assertFalse(dialog.top.overrideredirect())
                style, _attrs = dialog.top.tk.call("::tk::unsupported::MacWindowStyle", "style", dialog.top)
                self.assertEqual(style, "overlay")
            else:
                self.assertTrue(dialog.top.overrideredirect())
            _advance_frame(dialog)
            self.assertGreater(dialog.index, 1)
            again = SpinnerDialog(root, "Again")
            self.assertIs(again.frames, dialog.frames)
            again.close()
            dialog.close()
            dialog.close()
            self.assertFalse(dialog.top.winfo_exists())
        finally:
            root.destroy()
