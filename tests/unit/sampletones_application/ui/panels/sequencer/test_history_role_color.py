import pytest

from sampletones_application.layout.config import LayoutConfig
from sampletones_application.layout.loader import load_layout_config
from sampletones_application.paths import (
    BEHAVIOR_DIRECTORY,
    LAYOUT_DIRECTORY,
    PALETTES_DIRECTORY,
)
from sampletones_application.ui.panels.sequencer.history import GUISequencerHistoryPanel
from sampletones_application.utils.palette.catalog import PaletteCatalog
from sampletones_application.utils.palette.source import PaletteSource
from sampletones_application.view_model.shared.history import HistoryDetailRole


@pytest.fixture
def layout_config() -> LayoutConfig:
    source = PaletteSource(PaletteCatalog.load(PALETTES_DIRECTORY).default)
    return load_layout_config(LAYOUT_DIRECTORY, BEHAVIOR_DIRECTORY, source)


@pytest.fixture
def panel(layout_config: LayoutConfig) -> GUISequencerHistoryPanel:
    """Builds a panel without its DearPyGui-dependent constructor.

    A role's colour is read from the layout alone, so a running GUI context is unnecessary here.
    """
    instance = GUISequencerHistoryPanel.__new__(GUISequencerHistoryPanel)
    instance._layout = layout_config.tabs.sequencer
    instance._feature_colors = layout_config.general.colors.features
    return instance


class TestWhatColourAVoiceRoleWears:
    """A history line names its voice in the colour of the kind that voice is."""

    def test_a_sample_wears_the_sample_colour(
        self,
        panel: GUISequencerHistoryPanel,
        layout_config: LayoutConfig,
    ) -> None:
        text = layout_config.tabs.sequencer.colors.text

        assert panel._role_color(HistoryDetailRole.SAMPLE) is text.sample

    def test_an_instrument_wears_the_instrument_colour(
        self,
        panel: GUISequencerHistoryPanel,
        layout_config: LayoutConfig,
    ) -> None:
        text = layout_config.tabs.sequencer.colors.text

        assert panel._role_color(HistoryDetailRole.INSTRUMENT) is text.instrument

    def test_a_voice_of_no_stated_kind_wears_the_slot_colour(
        self,
        panel: GUISequencerHistoryPanel,
        layout_config: LayoutConfig,
    ) -> None:
        """The tracker's voice slot and a voice the pool dropped read as one thing."""
        text = layout_config.tabs.sequencer.colors.text

        assert panel._role_color(HistoryDetailRole.VOICE) is text.voice

    def test_the_two_kinds_are_told_apart(self, panel: GUISequencerHistoryPanel) -> None:
        sample = panel._role_color(HistoryDetailRole.SAMPLE)
        instrument = panel._role_color(HistoryDetailRole.INSTRUMENT)

        assert sample.rgba != instrument.rgba

    def test_every_role_answers_with_a_colour(self, panel: GUISequencerHistoryPanel) -> None:
        """The panel paints whatever the logic tags, so each role states what it wears."""
        for role in HistoryDetailRole:
            assert panel._role_color(role) is not None
