from typing import Any, Dict, List, Tuple

import pytest

from sampletones_application.ui.panels.sequencer import channels as channels_module
from sampletones_application.ui.panels.sequencer.channels import (
    ChannelMenuLabels,
    ChannelSwitch,
    channel_tooltip,
)
from sampletones_core.constants.enums import GeneratorName

LABELS = ChannelMenuLabels(
    mute="Mute",
    unmute="Unmute",
    solo="Solo",
    unsolo="Unsolo",
    mute_all="Mute all channels",
    unmute_all="Unmute all channels",
)


class _MenuRecorder:
    def __init__(self) -> None:
        self.items: List[Tuple[str, bool]] = []

    def add_menu_item(self, **kwargs: Any) -> int:
        self.items.append((kwargs["label"], kwargs.get("enabled", True)))
        return 0

    def add_separator(self, **kwargs: Any) -> int:
        return 0

    @property
    def labels(self) -> List[str]:
        return [label for label, _ in self.items]

    def is_enabled(self, label: str) -> bool:
        return dict(self.items)[label]


def _switch() -> ChannelSwitch:
    """A switch whose hooks are inert, for reading the items it builds."""
    return ChannelSwitch(
        labels=LABELS,
        on_mute_toggled=lambda generator: None,
        on_soloed=lambda generator: None,
        on_toggled=lambda: None,
        on_muted=lambda: None,
        on_unmuted=lambda: None,
    )


@pytest.fixture
def menu(monkeypatch: pytest.MonkeyPatch) -> _MenuRecorder:
    instance = _MenuRecorder()
    monkeypatch.setattr(channels_module.dpg, "add_menu_item", instance.add_menu_item)
    monkeypatch.setattr(channels_module.dpg, "add_separator", instance.add_separator)
    return instance


class TestMenuBeforeTheFirstModel:
    """A table whose menu opens before the first mute set arrives reads every channel as audible."""

    def test_a_channel_offers_to_mute_and_to_solo(self, menu: _MenuRecorder) -> None:
        _switch().add_menu_items(GeneratorName.TRIANGLE, None)

        assert menu.labels == [
            LABELS.mute,
            LABELS.solo,
            LABELS.mute_all,
            LABELS.unmute_all,
        ]

    def test_muting_everything_is_offered_and_restoring_is_withheld(self, menu: _MenuRecorder) -> None:
        _switch().add_menu_items(None, None)

        assert menu.is_enabled(LABELS.mute_all)
        assert not menu.is_enabled(LABELS.unmute_all)


class TestChannelTooltip:
    def test_the_modifier_is_spelled_into_the_template(self) -> None:
        assert channel_tooltip("{modifier}+click to solo it.") == "Ctrl+click to solo it."

    def test_a_template_naming_no_modifier_is_left_as_it_stands(self) -> None:
        assert channel_tooltip("Click to mute this channel.") == "Click to mute this channel."


class TestClickRouting:
    def test_a_channel_click_carries_its_channel(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(channels_module.dpg, "set_value", lambda item, value: None)
        monkeypatch.setattr(channels_module, "capture_modifiers", frozenset)
        toggled: List[GeneratorName] = []
        switch = ChannelSwitch(
            labels=LABELS,
            on_mute_toggled=toggled.append,
            on_soloed=lambda generator: pytest.fail("a plain click must not solo"),
            on_toggled=lambda: pytest.fail("a channel click addresses one channel"),
            on_muted=lambda: None,
            on_unmuted=lambda: None,
        )

        switch.click(0, GeneratorName.PULSE1)

        assert toggled == [GeneratorName.PULSE1]

    def test_the_click_releases_the_selectable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        released: Dict[int, bool] = {}
        monkeypatch.setattr(channels_module.dpg, "set_value", released.__setitem__)
        monkeypatch.setattr(channels_module, "capture_modifiers", frozenset)

        _switch().click(77, None)

        assert released == {77: False}
