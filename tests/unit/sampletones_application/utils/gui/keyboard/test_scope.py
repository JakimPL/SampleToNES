from dataclasses import dataclass

import pytest

from sampletones_application.utils.gui.keyboard import KeyRouter, focus, panel_scope_active
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase


@pytest.fixture(autouse=True)
def no_focused_field(monkeypatch: pytest.MonkeyPatch) -> None:
    """No text field is being edited, so a case names what it is about and nothing beside it."""
    monkeypatch.setattr(focus, "is_field_focused", lambda: False)


class TestWhatAPanelScopeAnswersTo(BaseTestSuite):
    """A panel owns the next key while every condition its scope names holds at once."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        """One reading of the four conditions, and whether the panel owns the press."""

        tab_active: bool
        card_open: bool
        holds: bool
        expected: bool

    test_cases = (
        TestCase(label="everything stands", tab_active=True, card_open=True, holds=True, expected=True),
        TestCase(label="another tab is in front", tab_active=False, card_open=True, holds=True, expected=False),
        TestCase(label="the card is put away", tab_active=True, card_open=False, holds=True, expected=False),
        TestCase(label="the panel holds nothing", tab_active=True, card_open=True, holds=False, expected=False),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_scope_answers_where_every_condition_holds(self, test_case: TestCase) -> None:
        active = panel_scope_active(
            tab_active=lambda: test_case.tab_active,
            router=KeyRouter(),
            holds=test_case.holds,
            card_open=lambda: test_case.card_open,
        )

        assert active is test_case.expected

    def test_a_field_holding_the_keyboard_stands_the_panel_down(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A reader typing keeps the plain keys, whatever the panel behind the field holds."""
        monkeypatch.setattr(focus, "is_field_focused", lambda: True)

        active = panel_scope_active(
            tab_active=lambda: True,
            router=KeyRouter(),
            holds=True,
            card_open=lambda: True,
        )

        assert active is False
