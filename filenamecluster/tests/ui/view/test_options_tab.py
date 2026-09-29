"""OptionsTab: the logging switch and the read-only learned-model table."""

import json

from filenamecluster.log import logging_enabled
from conftest import WindowCase


class OptionsTabTests(WindowCase):
    def test_options_logging_switch_starts_off(self):
        self.assertEqual(self.app.view.logging_switch.cget("text"), "Write application log")
        self.assertFalse(self.app.view.logging_var.get())
        self.assertFalse(logging_enabled())
        self.app.view.logging_var.set(True)
        self.app.view._on_logging()
        self.assertTrue(logging_enabled())
        self.app.view.logging_var.set(False)
        self.app.view._on_logging()
        self.assertFalse(logging_enabled())

    def test_options_model_view_matches_the_json_and_stays_read_only(self):
        self.assertEqual(
            [self.app.view.model_tree.set(row, "value") for row in self.app.view.model_tree.get_children()],
            ["—", "—", "—", "—"],
        )
        self.assertEqual(self.app.view.model_tree.bind("<Double-1>"), "")
        self.app.controller.load_folder(self.folder)
        raw = json.loads((self.folder / "filenamecluster-model.json").read_text(encoding="utf-8"))
        self.assertIsNone(raw["learned"])
        self.assertEqual(
            [self.app.view.model_tree.set(row, "value") for row in ("within_hours", "between_hours", "boundary_hours", "separated")],
            ["null", "null", "null", "null"],
        )

        rich = self.folder / "rich"
        rich.mkdir()
        for name in (
            "IMG_20240101_100000.jpg",
            "IMG_20240101_140000.jpg",
            "IMG_20240101_200000.jpg",
            "IMG_20240102_040000.jpg",
            "IMG_20240104_040000.jpg",
            "IMG_20240107_040000.jpg",
            "IMG_20240111_040000.jpg",
        ):
            (rich / name).write_bytes(b"x")
        self.app.controller.load_folder(rich)
        learned = json.loads((rich / "filenamecluster-model.json").read_text(encoding="utf-8"))["learned"]
        self.assertIsNotNone(learned)
        for key in ("within_hours", "between_hours", "boundary_hours"):
            self.assertEqual(self.app.view.model_tree.set(key, "parameter"), f"learned.{key}")
            self.assertEqual(self.app.view.model_tree.set(key, "value"), json.dumps(learned[key]))
        self.assertEqual(
            self.app.view.model_tree.set("separated", "value"),
            "true" if learned["separated"] else "false",
        )
        self.assertIsNone(self.app.view._pattern_editor)
        raw_options = json.loads((rich / "filenamecluster-model.json").read_text(encoding="utf-8"))
        self.assertIn("options", raw_options)
        self.assertEqual(
            str(raw_options["options"]["floor_hours"]),
            self.app.view.option_vars["floor"].get(),
        )
