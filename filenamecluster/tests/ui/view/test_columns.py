"""EqualColumns: the Options panes wrap their hints and share the width."""


from conftest import WindowCase


class ColumnTests(WindowCase):
    def test_options_panes_wrap_and_share_the_width(self):
        self.assertEqual(str(self.app.view.options_rows.cget("orient")), "vertical")
        self.assertEqual(str(self.app.view.options_columns.cget("orient")), "horizontal")
        self.assertEqual(len(self.app.view.options_rows.panes()), 2)
        self.assertEqual(len(self.app.view.options_columns.panes()), 3)
        limits = self.app.root.nametowidget(self.app.view.options_columns.panes()[1])
        limits.event_generate("<Configure>", width=520, height=400)
        hints = [
            child
            for child in limits.winfo_children()
            if str(child.cget("style")) == "Muted.TLabel"
        ]
        self.assertEqual(int(hints[0].cget("wraplength")), 492)
        patterns = self.app.root.nametowidget(self.app.view.options_rows.panes()[0])
        patterns.event_generate("<Configure>", width=420, height=300)
        self.assertEqual(int(patterns.winfo_children()[0].cget("wraplength")), 400)
        self.app.view._place_equal_columns(self.app.view.options_columns.winfo_width() or 900)
        widths = [
            int(self.app.view.options_columns.paneconfigure(pane_id, "width")[-1])
            for pane_id in self.app.view.options_columns.panes()
        ]
        self.assertEqual(widths[0], widths[1])
        self.assertEqual(widths[1], widths[2])
        self.assertGreater(widths[0], 0)
