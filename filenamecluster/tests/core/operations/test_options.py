"""OptionReader: option text the controller refuses, and why."""


from conftest import WindowCase


class OptionReaderTests(WindowCase):
    def test_bad_options_are_reported(self):
        self.app.controller.load_folder(self.folder)
        self.app.view.option_vars["floor"].set(800)
        self.app.controller.refresh()
        self.assertIn("ceiling", self.app.view.status_text.get())
        self.assertEqual(str(self.app.view.status.cget("style")), "Error.TLabel")
        self.app.controller.revise_option("floor", "abc")
        self.app.controller.refresh()
        self.assertIn("Never split", self.app.view.status_text.get())
        self.app.controller.restore_defaults()
        self.assertEqual(len(self.app.model.result.clusters), 2)

    def test_year_window_and_priorities_are_checked(self):
        self.app.controller.load_folder(self.folder)
        self.assertEqual(self.app.view.limit_vars["min_year"].get(), "1990")
        self.assertEqual(self.app.view.limit_vars["prec_clock"].get(), "30")
        self.app.view.limit_vars["min_year"].set(2100)
        self.app.view.limit_vars["max_year"].set(1990)
        self.app.controller.refresh()
        self.assertIn("minimum year", self.app.view.status_text.get())

        self.app.view.limit_vars["min_year"].set(0)
        self.app.controller.refresh()
        self.assertIn("between", self.app.view.status_text.get())

        self.app.controller.revise_limit("min_year", "nope")
        self.app.view.limit_vars["max_year"].set(2100)
        self.app.controller.refresh()
        self.assertIn("Minimum year", self.app.view.status_text.get())

        self.app.controller.restore_defaults()
        self.assertEqual(len(self.app.model.result.clusters), 2)
        self.assertEqual(self.app.view.limit_vars["min_year"].get(), "1990")
