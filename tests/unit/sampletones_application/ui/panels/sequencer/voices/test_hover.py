from typing import Final, Iterator, Optional, Tuple
from unittest.mock import MagicMock

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.paths import LANG_EN
from sampletones_application.ui.panels.sequencer.voices.footprint import (
    VoiceFootprintText,
)
from sampletones_application.ui.panels.sequencer.voices.panel import (
    GUISequencerVoicesPanel,
)
from sampletones_application.view_model.sequencer.voices import (
    VoiceEntryViewModel,
    VoiceKind,
)
from sampletones_application.view_model.shared.footprint import VoiceFootprintViewModel
from sampletones_core.constants.enums import ChannelName
from sampletones_core.formats.famitracker.footprint import InstrumentFootprint

SAMPLE_ID: Final[str] = "kick-id"
INSTRUMENT_ID: Final[str] = "lead-id"
UNKNOWN_ID: Final[str] = "gone-id"

ENTRIES: Final[Tuple[VoiceEntryViewModel, ...]] = (
    VoiceEntryViewModel(voice_id=SAMPLE_ID, name="Kick", kind=VoiceKind.SAMPLE),
    VoiceEntryViewModel(voice_id=INSTRUMENT_ID, name="Lead", kind=VoiceKind.INSTRUMENT),
)

PULSE_1_FOOTPRINT: Final[InstrumentFootprint] = InstrumentFootprint(instrument_bytes=9, sequence_bytes=32)
NOISE_FOOTPRINT: Final[InstrumentFootprint] = InstrumentFootprint(instrument_bytes=7, sequence_bytes=12)
SAMPLE_FOOTPRINT: Final[VoiceFootprintViewModel] = VoiceFootprintViewModel.from_footprints(
    {
        ChannelName.PULSE1: PULSE_1_FOOTPRINT,
        ChannelName.NOISE: NOISE_FOOTPRINT,
    }
)
INSTRUMENT_FOOTPRINT: Final[VoiceFootprintViewModel] = VoiceFootprintViewModel.from_instrument(PULSE_1_FOOTPRINT)


def _panel(footprint: Optional[VoiceFootprintViewModel]) -> GUISequencerVoicesPanel:
    """The panel over the facts a hovered row reads, with no DearPyGui context behind it."""
    language_manager = LanguageManager(LANG_EN)
    panel = GUISequencerVoicesPanel.__new__(GUISequencerVoicesPanel)
    panel._entries = ENTRIES
    panel._footprint_text = VoiceFootprintText(language_manager)
    panel._tpl_status_sample = language_manager["sequencer.voices.template.status_sample"]
    panel._tpl_status_instrument = language_manager["sequencer.voices.template.status_instrument"]
    panel._channel_separator = language_manager["sequencer.voices.template.status_channel_separator"]
    panel.voice_footprint = lambda _voice_id: footprint
    return panel


class TestWhatARowSaysAboutItsVoice:
    def test_a_sample_names_the_channels_it_plays(self) -> None:
        message = _panel(SAMPLE_FOOTPRINT)._voice_status_message(SAMPLE_ID)

        assert "Pulse 1" in message
        assert "Noise" in message
        assert "Pulse 2" not in message

    def test_a_sample_states_what_it_costs_as_one_figure(self) -> None:
        message = _panel(SAMPLE_FOOTPRINT)._voice_status_message(SAMPLE_ID)

        assert f"{SAMPLE_FOOTPRINT.total_bytes} B" in message

    def test_a_sample_is_named_and_called_a_sample(self) -> None:
        message = _panel(SAMPLE_FOOTPRINT)._voice_status_message(SAMPLE_ID)

        assert message.startswith("Kick")
        assert "sample" in message

    def test_an_instrument_names_no_channel_and_says_every_one_can_play_it(self) -> None:
        message = _panel(INSTRUMENT_FOOTPRINT)._voice_status_message(INSTRUMENT_ID)

        assert message.startswith("Lead")
        assert "instrument" in message
        assert "Pulse 1" not in message
        assert f"{PULSE_1_FOOTPRINT.total_bytes} B" in message

    @pytest.mark.parametrize(
        ("voice_id", "footprint"),
        [
            (UNKNOWN_ID, SAMPLE_FOOTPRINT),
            (SAMPLE_ID, None),
        ],
        ids=["voice_the_pool_no_longer_holds", "voice_nothing_measures"],
    )
    def test_a_voice_with_nothing_to_state_says_nothing(
        self,
        voice_id: str,
        footprint: Optional[VoiceFootprintViewModel],
    ) -> None:
        assert _panel(footprint)._voice_status_message(voice_id) == ""


@pytest.fixture
def dpg_context() -> Iterator[None]:
    dpg.create_context()
    try:
        yield
    finally:
        dpg.destroy_context()


@pytest.fixture
def hovered_panel() -> GUISequencerVoicesPanel:
    """The panel over the facts a hovered row reads, saying what it says to a recorded status bar."""
    panel = _panel(SAMPLE_FOOTPRINT)
    panel._status_bar = MagicMock()
    return panel


def _row(voice_id: str) -> int:
    """A row of the list, carrying the position and the voice the list gives each row."""
    with dpg.window():
        return int(dpg.add_selectable(label=voice_id, user_data=(0, voice_id)))


class TestAHoverReachingTheList:
    """A hover is answered a frame after it happened, and the list rebuilds every row on each update."""

    def test_a_hover_on_a_standing_row_says_what_its_voice_is(
        self,
        dpg_context: None,
        hovered_panel: GUISequencerVoicesPanel,
    ) -> None:
        row = _row(SAMPLE_ID)

        hovered_panel._on_row_hovered(row, row)

        hovered_panel._status_bar.set.assert_called_once_with(hovered_panel._voice_status_message(SAMPLE_ID))

    def test_a_hover_reaching_a_row_that_is_gone_says_nothing(
        self,
        dpg_context: None,
        hovered_panel: GUISequencerVoicesPanel,
    ) -> None:
        gone = _row(SAMPLE_ID)
        dpg.delete_item(gone)

        hovered_panel._on_row_hovered(gone, gone)

        hovered_panel._status_bar.set.assert_not_called()
        standing = _row(SAMPLE_ID)
        hovered_panel._on_row_hovered(standing, standing)
        hovered_panel._status_bar.set.assert_called_once()
