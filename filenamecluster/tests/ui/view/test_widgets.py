"""WidgetKit: the input lock disables controls and leaves the drawings usable."""


from conftest import WindowCase


class InputLockTests(WindowCase):
    def test_lock_inputs_disables_buttons_and_options_only(self):
        self.app.controller.load_folder(self.folder)
        self.assertNotIn("disabled", self.app.view.apply_button.state())
        self.app.view.lock_inputs()
        self.assertIn("disabled", self.app.view.apply_button.state())
        self.assertEqual(str(self.app.view.option_inputs["floor"].cget("state")), "disabled")
        self.assertEqual(str(self.app.view.limit_inputs["min_year"].cget("state")), "disabled")
        self.assertEqual(str(self.app.view.logging_switch.cget("state")), "disabled")
        self.app.view._begin_pattern_edit(self.app.view.pattern_tree.get_children()[0], "pattern")
        self.assertIsNone(self.app.view._pattern_editor)
        self.assertEqual(str(self.app.view.overview.canvas.cget("state")), "normal")
        self.assertEqual(str(self.app.view.calendar.canvas.cget("state")), "normal")
        self.assertEqual(str(self.app.view.cluster_tree.cget("selectmode")), "browse")
        self.app.view.unlock_inputs()
        self.assertNotIn("disabled", self.app.view.apply_button.state())
        self.assertIn("disabled", self.app.view.flatten_button.state())
