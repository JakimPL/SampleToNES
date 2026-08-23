import pytest

from sampletones_application.layout.config import LayoutConfig
from sampletones_application.layout.loader import load_layout_config
from sampletones_application.layout.tabs.sequencer import SequencerLayout
from sampletones_application.paths import (
    BEHAVIOR_DIRECTORY,
    LAYOUT_DIRECTORY,
    PALETTES_DIRECTORY,
)
from sampletones_application.ui.panels.sequencer.voices.panel import GUISequencerVoicesPanel
from sampletones_application.utils.palette.catalog import PaletteCatalog
from sampletones_application.utils.palette.source import PaletteSource
from sampletones_application.view_model.sequencer.voices import VoiceKind


@pytest.fixture
def layout_config() -> LayoutConfig:
    source = PaletteSource(PaletteCatalog.load(PALETTES_DIRECTORY).default)
    return load_layout_config(LAYOUT_DIRECTORY, BEHAVIOR_DIRECTORY, source)


@pytest.fixture
def sequencer_layout(layout_config: LayoutConfig) -> SequencerLayout:
    return layout_config.tabs.sequencer


def _panel(sequencer_layout: SequencerLayout) -> GUISequencerVoicesPanel:
    """Builds a panel without its DearPyGui-dependent constructor.

    The kind's colour is read from the layout alone, so a running GUI context is unnecessary here.
    """
    panel = GUISequencerVoicesPanel.__new__(GUISequencerVoicesPanel)
    panel._layout = sequencer_layout
    return panel


class TestWhatColourAKindWears:
    def test_a_sample_wears_the_sample_colour(self, sequencer_layout: SequencerLayout) -> None:
        panel = _panel(sequencer_layout)

        assert panel._kind_color(VoiceKind.SAMPLE) is sequencer_layout.colors.text.sample

    def test_an_instrument_wears_the_instrument_colour(self, sequencer_layout: SequencerLayout) -> None:
        panel = _panel(sequencer_layout)

        assert panel._kind_color(VoiceKind.INSTRUMENT) is sequencer_layout.colors.text.instrument

    def test_the_two_kinds_are_told_apart(self, sequencer_layout: SequencerLayout) -> None:
        """The colour carries the kind, so a list of one hue would say nothing the glyph does not."""
        panel = _panel(sequencer_layout)

        assert panel._kind_color(VoiceKind.SAMPLE).rgba != panel._kind_color(VoiceKind.INSTRUMENT).rgba
