from dataclasses import dataclass
from typing import Dict, FrozenSet, List

import pytest

from sampletones_application.ui.panels.reconstruction import plot as plot_module
from sampletones_application.ui.panels.reconstruction.plot import (
    GUIReconstructionPlotPanel,
)
from sampletones_application.view_model.reconstruction.reconstruction import (
    ReconstructionPathState,
    ReconstructionPathViewModel,
    ReconstructionViewModel,
)
from sampletones_core.constants.enums import GeneratorName
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

ALL_GENERATORS = frozenset(GeneratorName)


class StubTheme:
    """Stands in for a registered theme, recording the items it was bound to."""

    def __init__(self, tag: str, bindings: Dict[str, str]) -> None:
        self.tag = tag
        self._bindings = bindings

    def bind_to_item(self, item: str) -> None:
        self._bindings[item] = self.tag


class Harness:
    """The panel over its generator checkboxes, each shown or disabled as a reconstruction leaves
    it."""

    def __init__(
        self,
        *,
        selected: FrozenSet[GeneratorName],
        available: FrozenSet[GeneratorName],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        self.values: Dict[str, bool] = {self._tag(generator): generator in selected for generator in GeneratorName}
        self.enabled: Dict[str, bool] = {self._tag(generator): generator in available for generator in GeneratorName}
        self.reported: List[List[GeneratorName]] = []
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
        self.panel.on_generators_changed = self.reported.append

    def _configure(self, tag: str, *, enabled: bool, default_value: bool) -> None:
        self.enabled[tag] = enabled
        self.values[tag] = default_value

    @staticmethod
    def _tag(generator: GeneratorName) -> str:
        return GUIReconstructionPlotPanel._get_generator_checkbox_tag(generator)

    def offered(self) -> FrozenSet[GeneratorName]:
        return frozenset(generator for generator in GeneratorName if self.enabled[self._tag(generator)])

    def selected(self) -> FrozenSet[GeneratorName]:
        return frozenset(generator for generator in GeneratorName if self.values[self._tag(generator)])


def _view_model(
    playing: FrozenSet[GeneratorName],
    selected: FrozenSet[GeneratorName],
) -> ReconstructionViewModel:
    empty_path = ReconstructionPathViewModel(state=ReconstructionPathState.EMPTY, path="")
    return ReconstructionViewModel(
        reconstruction_loaded=True,
        playing_generators=playing,
        selected_generators=selected,
        reconstruction_file=empty_path,
        original_audio=empty_path,
    )


class TestGeneratorCheckboxes:
    """The checkboxes offer the channels that play and tick the ones the reader keeps on."""

    def test_a_channel_that_plays_is_offered(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        harness = Harness(selected=frozenset(), available=frozenset(), monkeypatch=monkeypatch)
        playing = frozenset({GeneratorName.PULSE1, GeneratorName.NOISE})

        harness.panel.update_view(_view_model(playing, playing))

        assert harness.offered() == playing
        assert harness.selected() == playing

    def test_a_channel_switched_off_by_hand_stays_off(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """An edit reports the view again, and the report carries the reader's choice."""
        harness = Harness(selected=ALL_GENERATORS, available=ALL_GENERATORS, monkeypatch=monkeypatch)
        playing = frozenset({GeneratorName.PULSE1, GeneratorName.NOISE})

        harness.panel.update_view(_view_model(playing, frozenset({GeneratorName.NOISE})))

        assert harness.offered() == playing
        assert harness.selected() == frozenset({GeneratorName.NOISE})

    def test_a_channel_standing_by_is_left_unticked(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        harness = Harness(selected=ALL_GENERATORS, available=ALL_GENERATORS, monkeypatch=monkeypatch)
        playing = frozenset({GeneratorName.PULSE1})

        harness.panel.update_view(_view_model(playing, playing))

        assert harness.selected() == playing
        assert GeneratorName.PULSE2 not in harness.offered()

    def test_a_channel_that_plays_carries_its_own_tint(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        harness = Harness(selected=frozenset(), available=frozenset(), monkeypatch=monkeypatch)
        playing = frozenset({GeneratorName.TRIANGLE})

        harness.panel.update_view(_view_model(playing, playing))

        assert set(harness.bound_themes) == {Harness._tag(GeneratorName.TRIANGLE)}


class TestToggleGenerator(BaseTestSuite):
    """The key a channel answers to switches its slice in and out of the waveform."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        selected: FrozenSet[GeneratorName]
        available: FrozenSet[GeneratorName]
        generator: GeneratorName
        expected: FrozenSet[GeneratorName]

    test_cases = (
        TestCase(
            label="switching a shown slice out",
            selected=ALL_GENERATORS,
            available=ALL_GENERATORS,
            generator=GeneratorName.PULSE1,
            expected=ALL_GENERATORS - {GeneratorName.PULSE1},
        ),
        TestCase(
            label="switching a hidden slice back in",
            selected=frozenset({GeneratorName.NOISE}),
            available=ALL_GENERATORS,
            generator=GeneratorName.TRIANGLE,
            expected=frozenset({GeneratorName.TRIANGLE, GeneratorName.NOISE}),
        ),
        TestCase(
            label="a generator the reconstruction holds none of stays out",
            selected=frozenset({GeneratorName.PULSE1}),
            available=frozenset({GeneratorName.PULSE1}),
            generator=GeneratorName.NOISE,
            expected=frozenset({GeneratorName.PULSE1}),
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

        harness.panel.toggle_generator(test_case.generator)

        assert harness.selected() == test_case.expected

    @pytest.mark.parametrize(
        "test_case",
        [test_case for test_case in test_cases if test_case.generator in test_case.available],
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

        harness.panel.toggle_generator(test_case.generator)

        assert harness.reported == [
            [generator for generator in GeneratorName if generator in test_case.expected],
        ]

    def test_a_generator_the_reconstruction_holds_none_of_reports_nothing(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Its checkbox already reads as unavailable, so the key leaves the waveform as it stands."""
        harness = Harness(
            selected=frozenset({GeneratorName.PULSE1}),
            available=frozenset({GeneratorName.PULSE1}),
            monkeypatch=monkeypatch,
        )

        harness.panel.toggle_generator(GeneratorName.NOISE)

        assert harness.reported == []

    def test_switching_a_slice_twice_returns_the_waveform_it_started_from(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        harness = Harness(
            selected=ALL_GENERATORS,
            available=ALL_GENERATORS,
            monkeypatch=monkeypatch,
        )

        harness.panel.toggle_generator(GeneratorName.PULSE2)
        harness.panel.toggle_generator(GeneratorName.PULSE2)

        assert harness.selected() == ALL_GENERATORS
