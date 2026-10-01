"""ClashResolver records replace, skip, apply-to-all, and cancel."""

import unittest
from pathlib import Path

from filenamecluster.core.operations.placement import PlannedMove
from filenamecluster.ui.controller.clashes import ClashResolver
from filenamecluster.ui.model import ClashChoice


class _Ui:
    def __init__(self, answers):
        self.answers = answers
        self.asked = []

    def resolve_clash(self, clash):
        self.asked.append(clash.name)
        choice, for_all, cancelled = self.answers.pop(0)
        clash.choice = choice
        clash.for_all = for_all
        clash.cancelled = cancelled


def move(name: str) -> PlannedMove:
    return PlannedMove(Path(f"from/{name}"), Path(f"to/{name}"))


class ResolverTests(unittest.TestCase):
    def test_replace_skip_and_one_answer_for_every_remaining_clash(self):
        first, second, third = move("a.jpg"), move("b.jpg"), move("c.jpg")
        ui = _Ui([(ClashChoice.REPLACE, False, False), (ClashChoice.SKIP, True, False)])
        chosen = ClashResolver(ui).replacing([first, second, third])
        self.assertEqual(chosen, frozenset({first.source.resolve()}))
        self.assertEqual(ui.asked, ["a.jpg", "b.jpg"])

    def test_closing_the_dialog_cancels_before_any_choice_is_kept(self):
        ui = _Ui([(ClashChoice.REPLACE, False, True)])
        self.assertIsNone(ClashResolver(ui).replacing([move("a.jpg"), move("b.jpg")]))
        self.assertEqual(ui.asked, ["a.jpg"])

    def test_no_clashes_need_no_question(self):
        self.assertEqual(ClashResolver(_Ui([])).replacing(()), frozenset())
