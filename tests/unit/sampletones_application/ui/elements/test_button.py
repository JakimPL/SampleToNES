from typing import Any, Dict, List, Tuple

import pytest

from sampletones_application.ui.elements import button as button_module
from sampletones_application.ui.elements.button import GUIButton

GROUP_TAG = "probe_button"
INNER_TAG = "probe_button_button"


def _button() -> GUIButton:
    """A button carrying only the tags the tested methods touch, bypassing the DearPyGui-dependent
    constructor."""
    instance = GUIButton.__new__(GUIButton)
    instance._tag = GROUP_TAG
    instance._button_tag = INNER_TAG
    return instance


@pytest.fixture
def configured(monkeypatch: pytest.MonkeyPatch) -> List[Tuple[str, Dict[str, Any]]]:
    calls: List[Tuple[str, Dict[str, Any]]] = []

    def record(tag: str, **kwargs: Any) -> None:
        calls.append((tag, kwargs))

    monkeypatch.setattr(button_module.dpg, "configure_item", record)
    return calls


class TestSetEnabled:
    """DearPyGui gates a press on the button's own state and on that of its wrapper group, so both
    items carry the state the caller asked for."""

    def test_enabling_reaches_the_group_and_the_button(
        self,
        configured: List[Tuple[str, Dict[str, Any]]],
    ) -> None:
        _button().set_enabled(True)

        assert configured == [
            (GROUP_TAG, {"enabled": True}),
            (INNER_TAG, {"enabled": True}),
        ]

    def test_disabling_reaches_the_group_and_the_button(
        self,
        configured: List[Tuple[str, Dict[str, Any]]],
    ) -> None:
        _button().set_enabled(False)

        assert configured == [
            (GROUP_TAG, {"enabled": False}),
            (INNER_TAG, {"enabled": False}),
        ]

    def test_configure_item_applies_the_enabled_state_to_both(
        self,
        configured: List[Tuple[str, Dict[str, Any]]],
    ) -> None:
        _button().configure_item(enabled=True)

        assert (GROUP_TAG, {"enabled": True}) in configured
        assert (INNER_TAG, {"enabled": True}) in configured
