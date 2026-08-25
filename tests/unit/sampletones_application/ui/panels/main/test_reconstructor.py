from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Tuple

import pytest

from sampletones_application.tags.main import TAG_MAIN_RECONSTRUCTOR_SLIDER_DRIVE
from sampletones_application.ui.panels.main import reconstructor as reconstructor_module
from sampletones_application.ui.panels.main.reconstructor import GUIReconstructorPanel
from sampletones_application.view_model.main.updates import GenerationSettingsUpdate
from sampletones_core.constants.enums import ChannelName
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

DRIVE = 1.5

ALL_CHANNELS = frozenset(ChannelName)


class Harness:
    """The panel over its checkboxes as DearPyGui holds them, without a window to hold them in."""

    def __init__(
        self,
        checked: FrozenSet[ChannelName],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        self.values: Dict[str, bool] = {
            GUIReconstructorPanel._get_generator_checkbox_tag(channel): channel in checked for channel in ChannelName
        }
        self.reported: List[GenerationSettingsUpdate] = []

        monkeypatch.setattr(reconstructor_module.dpg, "get_value", self.values.__getitem__)
        monkeypatch.setattr(reconstructor_module, "dpg_set_value", self.values.__setitem__)
        monkeypatch.setattr(reconstructor_module, "clamp_widget_value", self._drive)

        self.panel = GUIReconstructorPanel.__new__(GUIReconstructorPanel)
        self.panel.on_generation_settings_changed = self.reported.append

    @staticmethod
    def _drive(tag: str) -> float:
        assert tag == TAG_MAIN_RECONSTRUCTOR_SLIDER_DRIVE
        return DRIVE

    def checked(self) -> FrozenSet[ChannelName]:
        return frozenset(
            channel
            for channel in ChannelName
            if self.values[GUIReconstructorPanel._get_generator_checkbox_tag(channel)]
        )


class TestToggleChannel(BaseTestSuite):
    """The key a channel answers to switches its checkbox, the gesture a click on it makes."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        checked: FrozenSet[ChannelName]
        channel: ChannelName
        expected: FrozenSet[ChannelName]

    test_cases = (
        TestCase(
            label="switching one off leaves the rest",
            checked=ALL_CHANNELS,
            channel=ChannelName.TRIANGLE,
            expected=ALL_CHANNELS - {ChannelName.TRIANGLE},
        ),
        TestCase(
            label="switching one on adds it alone",
            checked=frozenset(),
            channel=ChannelName.PULSE1,
            expected=frozenset({ChannelName.PULSE1}),
        ),
        TestCase(
            label="the last one switched off leaves nothing selected",
            checked=frozenset({ChannelName.NOISE}),
            channel=ChannelName.NOISE,
            expected=frozenset(),
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_the_set_the_checkboxes_show(
        self,
        test_case: TestCase,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        harness = Harness(test_case.checked, monkeypatch)

        harness.panel.toggle_channel(test_case.channel)

        assert harness.checked() == test_case.expected

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_the_settings_the_panel_reports(
        self,
        test_case: TestCase,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A switch reaches the configuration the same way a click does, drive carried along."""
        harness = Harness(test_case.checked, monkeypatch)

        harness.panel.toggle_channel(test_case.channel)

        assert harness.reported == [
            GenerationSettingsUpdate(
                drive=DRIVE,
                channels=[channel for channel in ChannelName if channel in test_case.expected],
            )
        ]

    def test_switching_a_generator_twice_returns_the_set_it_started_from(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        harness = Harness(ALL_CHANNELS, monkeypatch)

        harness.panel.toggle_channel(ChannelName.PULSE2)
        harness.panel.toggle_channel(ChannelName.PULSE2)

        assert harness.checked() == ALL_CHANNELS

    def test_the_generators_are_reported_in_the_order_the_tracker_shows_them(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        harness = Harness(frozenset({ChannelName.NOISE, ChannelName.PULSE1}), monkeypatch)

        harness.panel.toggle_channel(ChannelName.TRIANGLE)

        assert self._generators(harness.reported) == [
            ChannelName.PULSE1,
            ChannelName.TRIANGLE,
            ChannelName.NOISE,
        ]

    @staticmethod
    def _generators(reported: List[GenerationSettingsUpdate]) -> List[ChannelName]:
        return list(reported[-1].channels)


class TestCheckboxTags:
    def test_each_generator_carries_a_tag_of_its_own(self) -> None:
        tags: Tuple[str, ...] = tuple(
            GUIReconstructorPanel._get_generator_checkbox_tag(channel) for channel in ChannelName
        )

        assert len(set(tags)) == len(tags)
