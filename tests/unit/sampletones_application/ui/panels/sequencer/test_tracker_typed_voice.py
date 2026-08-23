from typing import List, Optional, Tuple

import pytest

from sampletones_application.ui.elements.table.cells import EditableCells
from sampletones_application.ui.panels.sequencer import tracker as tracker_module
from sampletones_application.ui.panels.sequencer.input.edit import EditAction
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_application.view_model.sequencer.voices import (
    SequencerVoicesViewModel,
    VoiceEntryViewModel,
    VoiceKind,
)
from sampletones_core.constants.enums import ChannelName
from sampletones_core.utils.display import display_id

SAMPLE_INDEX = 0
INSTRUMENT_INDEX = 1
STORED_LABEL = display_id(None)

Write = Tuple[int, Optional[ChannelName], Optional[str]]


class Panel:
    """A tracker panel holding the pool and the cell cache a typed edit reads and writes.

    The commit path touches only those two and the ``on_set_row`` hook, so the widgets the labels
    are drawn on stay out of it and the reading under test is what the cache is left holding.
    """

    def __init__(self) -> None:
        self.panel = tracker_module.GUISequencerTrackerPanel.__new__(tracker_module.GUISequencerTrackerPanel)
        self.panel._editable_cells = EditableCells()
        self.panel._current_samples = SequencerVoicesViewModel(
            voices=(
                VoiceEntryViewModel(
                    voice_id="lead-id",
                    name="lead",
                    kind=VoiceKind.SAMPLE,
                    loop=False,
                ),
                VoiceEntryViewModel(
                    voice_id="pad-id",
                    name="pad",
                    kind=VoiceKind.INSTRUMENT,
                    loop=False,
                ),
            ),
        )
        self.writes: List[Write] = []
        self.panel.on_set_row = lambda row, channel, voice_id, transpose, volume: self.writes.append(
            (row, channel, voice_id)
        )

    def type_voice(self, index: int, channel: Optional[ChannelName]) -> None:
        self.panel._handle_edit_action(
            EditAction(
                row=0,
                channel=channel,
                sample_index=index,
                transpose=None,
                volume=None,
            )
        )

    def shown(self, channel: Optional[ChannelName]) -> str:
        """The label the cell cache holds, which is what the cell shows once the commit settles."""
        return self.panel._editable_cells.values.get((0, channel, SubColumn.VOICE), STORED_LABEL)


@pytest.fixture
def panel() -> Panel:
    return Panel()


class TestTypingAVoiceNumber:
    """The column a number is typed in decides whether the voice it names lands there."""

    def test_a_sample_typed_in_the_sample_column_is_written(self, panel: Panel) -> None:
        panel.type_voice(SAMPLE_INDEX, None)

        assert panel.writes == [(0, None, "lead-id")]
        assert panel.shown(None) == display_id(SAMPLE_INDEX)

    def test_an_instrument_typed_in_a_channel_column_is_written(self, panel: Panel) -> None:
        panel.type_voice(INSTRUMENT_INDEX, ChannelName.NOISE)

        assert panel.writes == [(0, ChannelName.NOISE, "pad-id")]
        assert panel.shown(ChannelName.NOISE) == display_id(INSTRUMENT_INDEX)

    def test_an_instrument_typed_in_the_sample_column_names_no_voice(self, panel: Panel) -> None:
        panel.type_voice(INSTRUMENT_INDEX, None)

        assert panel.writes == [(0, None, None)]

    def test_an_instrument_typed_in_the_sample_column_leaves_the_cell_showing_what_it_held(
        self,
        panel: Panel,
    ) -> None:
        """The refusal changes nothing, so a cell taking the number optimistically would keep it."""
        panel.type_voice(INSTRUMENT_INDEX, None)

        assert panel.shown(None) == STORED_LABEL

    def test_a_number_past_the_pool_reads_as_the_last_voice(self, panel: Panel) -> None:
        panel.type_voice(99, ChannelName.PULSE1)

        assert panel.writes == [(0, ChannelName.PULSE1, "pad-id")]

    def test_a_number_past_the_pool_still_answers_to_the_column(self, panel: Panel) -> None:
        """The last voice is the instrument, which the sample column stands by for."""
        panel.type_voice(99, None)

        assert panel.writes == [(0, None, None)]
        assert panel.shown(None) == STORED_LABEL

    def test_typing_into_an_empty_pool_names_no_voice(self, panel: Panel) -> None:
        panel.panel._current_samples = SequencerVoicesViewModel(voices=())

        panel.type_voice(SAMPLE_INDEX, ChannelName.PULSE1)

        assert panel.writes == [(0, ChannelName.PULSE1, None)]
        assert panel.shown(ChannelName.PULSE1) == STORED_LABEL
