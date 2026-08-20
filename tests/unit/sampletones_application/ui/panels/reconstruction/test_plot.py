from dataclasses import dataclass
from typing import Dict, FrozenSet, List

import pytest

from sampletones_application.ui.panels.reconstruction import plot as plot_module
from sampletones_application.ui.panels.reconstruction.plot import (
    GUIReconstructionPlotPanel,
)
from sampletones_application.view_model.reconstruction.paths.path import (
    ReconstructionPathViewModel,
)
from sampletones_application.view_model.reconstruction.paths.state import (
    ReconstructionPathState,
)
from sampletones_application.view_model.reconstruction.reconstruction import (
    ReconstructionViewModel,
)
from sampletones_core.constants.enums import ChannelName
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

ALL_CHANNELS = frozenset(ChannelName)


class StubTheme:
    """Stands in for a registered theme, recording the items it was bound to."""

    def __init__(self, tag: str, bindings: Dict[str, str]) -> None:
        self.tag = tag
        self._bindings = bindings

    def bind_to_item(self, item: str) -> None:
        self._bindings[item] = self.tag


class Harness:
    """The panel over its channel checkboxes, each shown or disabled as a reconstruction leaves
    it."""

    def __init__(
        self,
        *,
        selected: FrozenSet[ChannelName],
        available: FrozenSet[ChannelName],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        self.values: Dict[str, bool] = {self._tag(channel): channel in selected for channel in ChannelName}
        self.enabled: Dict[str, bool] = {self._tag(channel): channel in available for channel in ChannelName}
        self.reported: List[List[ChannelName]] = []
        self.bound_themes: Dict[str, str] = {}

        monkeypatch.setattr(plot_module.dpg, "get_value", self.values.__getitem__)
        monkeypatch.setattr(plot_module.dpg, "is_item_enabled", self.enabled.__getitem__)
        monkeypatch.setattr(plot_module.dpg, "bind_item_theme", lambda item, theme: self.bound_themes.pop(item, None))
        monkeypatch.setattr(plot_module, "dpg_set_value", self.values.__setitem__)
        monkeypatch.setattr(plot_module, "dpg_configure_item", self._configure)
        monkeypatch.setattr(
            plot_module.ThemeRegistry,
            "get",
            lambda tag: StubTheme(tag, self.bound_themes),
        )

        self.panel = GUIReconstructionPlotPanel.__new__(GUIReconstructionPlotPanel)
        self.panel.on_channels_changed = self.reported.append

    def _configure(self, tag: str, *, enabled: bool, default_value: bool) -> None:
        self.enabled[tag] = enabled
        self.values[tag] = default_value

    @staticmethod
    def _tag(channel: ChannelName) -> str:
        return GUIReconstructionPlotPanel._get_generator_checkbox_tag(channel)

    def offered(self) -> FrozenSet[ChannelName]:
        return frozenset(channel for channel in ChannelName if self.enabled[self._tag(channel)])

    def selected(self) -> FrozenSet[ChannelName]:
        return frozenset(channel for channel in ChannelName if self.values[self._tag(channel)])


def _view_model(
    playing: FrozenSet[ChannelName],
    selected: FrozenSet[ChannelName],
) -> ReconstructionViewModel:
    empty_path = ReconstructionPathViewModel(state=ReconstructionPathState.EMPTY, paths=())
    return ReconstructionViewModel(
        reconstruction_loaded=True,
        playing_channels=playing,
        selected_channels=selected,
        reconstruction_file=empty_path,
        original_audio=empty_path,
    )


class TestChannelCheckboxes:
    """The checkboxes offer the channels that play and tick the ones the reader keeps on."""

    def test_a_channel_that_plays_is_offered(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        harness = Harness(selected=frozenset(), available=frozenset(), monkeypatch=monkeypatch)
        playing = frozenset({ChannelName.PULSE1, ChannelName.NOISE})

        harness.panel.update_view(_view_model(playing, playing))

        assert harness.offered() == playing
        assert harness.selected() == playing

    def test_a_channel_switched_off_by_hand_stays_off(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """An edit reports the view again, and the report carries the reader's choice."""
        harness = Harness(selected=ALL_CHANNELS, available=ALL_CHANNELS, monkeypatch=monkeypatch)
        playing = frozenset({ChannelName.PULSE1, ChannelName.NOISE})

        harness.panel.update_view(_view_model(playing, frozenset({ChannelName.NOISE})))

        assert harness.offered() == playing
        assert harness.selected() == frozenset({ChannelName.NOISE})

    def test_a_channel_standing_by_is_left_unticked(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        harness = Harness(selected=ALL_CHANNELS, available=ALL_CHANNELS, monkeypatch=monkeypatch)
        playing = frozenset({ChannelName.PULSE1})

        harness.panel.update_view(_view_model(playing, playing))

        assert harness.selected() == playing
        assert ChannelName.PULSE2 not in harness.offered()

    def test_a_channel_that_plays_carries_its_own_tint(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        harness = Harness(selected=frozenset(), available=frozenset(), monkeypatch=monkeypatch)
        playing = frozenset({ChannelName.TRIANGLE})

        harness.panel.update_view(_view_model(playing, playing))

        assert set(harness.bound_themes) == {Harness._tag(ChannelName.TRIANGLE)}


class TestToggleChannel(BaseTestSuite):
    """The key a channel answers to switches its slice in and out of the waveform."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        selected: FrozenSet[ChannelName]
        available: FrozenSet[ChannelName]
        channel: ChannelName
        expected: FrozenSet[ChannelName]

    test_cases = (
        TestCase(
            label="switching a shown slice out",
            selected=ALL_CHANNELS,
            available=ALL_CHANNELS,
            channel=ChannelName.PULSE1,
            expected=ALL_CHANNELS - {ChannelName.PULSE1},
        ),
        TestCase(
            label="switching a hidden slice back in",
            selected=frozenset({ChannelName.NOISE}),
            available=ALL_CHANNELS,
            channel=ChannelName.TRIANGLE,
            expected=frozenset({ChannelName.TRIANGLE, ChannelName.NOISE}),
        ),
        TestCase(
            label="a channel the reconstruction holds none of stays out",
            selected=frozenset({ChannelName.PULSE1}),
            available=frozenset({ChannelName.PULSE1}),
            channel=ChannelName.NOISE,
            expected=frozenset({ChannelName.PULSE1}),
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_the_slices_the_checkboxes_show(
        self,
        test_case: TestCase,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        harness = Harness(
            selected=test_case.selected,
            available=test_case.available,
            monkeypatch=monkeypatch,
        )

        harness.panel.toggle_channel(test_case.channel)

        assert harness.selected() == test_case.expected

    @pytest.mark.parametrize(
        "test_case",
        [test_case for test_case in test_cases if test_case.channel in test_case.available],
        ids=lambda test_case: test_case.label,
    )
    def test_the_selection_the_panel_reports(
        self,
        test_case: TestCase,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A switch reaches the waveform and the audio the same way a click does."""
        harness = Harness(
            selected=test_case.selected,
            available=test_case.available,
            monkeypatch=monkeypatch,
        )

        harness.panel.toggle_channel(test_case.channel)

        assert harness.reported == [
            [channel for channel in ChannelName if channel in test_case.expected],
        ]

    def test_a_generator_the_reconstruction_holds_none_of_reports_nothing(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Its checkbox already reads as unavailable, so the key leaves the waveform as it stands."""
        harness = Harness(
            selected=frozenset({ChannelName.PULSE1}),
            available=frozenset({ChannelName.PULSE1}),
            monkeypatch=monkeypatch,
        )

        harness.panel.toggle_channel(ChannelName.NOISE)

        assert harness.reported == []

    def test_switching_a_slice_twice_returns_the_waveform_it_started_from(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        harness = Harness(
            selected=ALL_CHANNELS,
            available=ALL_CHANNELS,
            monkeypatch=monkeypatch,
        )

        harness.panel.toggle_channel(ChannelName.PULSE2)
        harness.panel.toggle_channel(ChannelName.PULSE2)

        assert harness.selected() == ALL_CHANNELS
