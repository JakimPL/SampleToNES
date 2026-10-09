from typing import List, Optional, Tuple

import pytest

from sampletones_application.ui.elements.table.cells import EditableCells
from sampletones_application.ui.panels.sequencer.input.edit import EditAction
from sampletones_application.ui.panels.sequencer.tracker import panel as tracker_module
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_application.view_model.sequencer.voices import (
    SequencerVoicesViewModel,
    VoiceEntryViewModel,
    VoiceKind,
    VoiceSelection,
)
from sampletones_core.constants.enums import ChannelName
from sampletones_core.project.patterns.pitch import Note, RowPitch
from sampletones_core.utils.display import display_id, display_pitch, display_volume

SAMPLE_INDEX = 0
INSTRUMENT_INDEX = 1
STORED_LABEL = display_id(None)
STORED_VOLUME = display_volume(None)
TYPED_VOLUME = 10
TYPED_NOTE = Note(value=60)
STORED_PITCH = display_pitch(None)
MARKS = {
    SAMPLE_INDEX: VoiceSelection(voice_id="lead-id", position=SAMPLE_INDEX, name="lead", kind=VoiceKind.SAMPLE),
    INSTRUMENT_INDEX: VoiceSelection(
        voice_id="pad-id",
        position=INSTRUMENT_INDEX,
        name="pad",
        kind=VoiceKind.INSTRUMENT,
    ),
}

Write = Tuple[int, Optional[ChannelName], Optional[str]]
Offset = Tuple[int, Optional[ChannelName], Optional[RowPitch], Optional[int]]


class Panel:
    """A tracker panel holding the pool and the cell cache a typed edit reads and writes.

    The commit path touches only those two, the rows the sample column takes a pitch or a volume
    on, and the ``on_set_row`` hook, so the widgets the labels are drawn on stay out of it and the
    reading under test is what the cache is left holding. No row starts out playing a sample.
    """

    def __init__(self) -> None:
        self.panel = tracker_module.GUISequencerTrackerPanel.__new__(tracker_module.GUISequencerTrackerPanel)
        self.panel._editable_cells = EditableCells()
        self.panel._cell_kinds = {}
        self.panel._current_samples = SequencerVoicesViewModel(
            voices=(
                VoiceEntryViewModel(
                    voice_id="lead-id",
                    name="lead",
                    kind=VoiceKind.SAMPLE,
                ),
                VoiceEntryViewModel(
                    voice_id="pad-id",
                    name="pad",
                    kind=VoiceKind.INSTRUMENT,
                ),
            ),
        )
        self.panel._rows_taking_offsets = frozenset()
        self.panel.marked_voice = None
        self.writes: List[Write] = []
        self.offsets: List[Offset] = []
        self.panel.on_set_row = self._record

    def _record(
        self,
        row: int,
        channel: Optional[ChannelName],
        voice_id: Optional[str],
        pitch: Optional[RowPitch],
        volume: Optional[int],
    ) -> None:
        self.writes.append((row, channel, voice_id))
        if pitch is not None or volume is not None:
            self.offsets.append((row, channel, pitch, volume))

    def mark(self, index: int) -> None:
        """Marks the voice at ``index`` in the voices list, as a click on its row does."""
        self.panel.marked_voice = lambda: MARKS[index]

    def type_pitch(self, pitch: RowPitch, channel: Optional[ChannelName]) -> None:
        self.panel._handle_edit_action(
            EditAction(
                row=0,
                channel=channel,
                sample_index=None,
                pitch=pitch,
                volume=None,
            )
        )

    def type_voice(self, index: int, channel: Optional[ChannelName]) -> None:
        self.panel._handle_edit_action(
            EditAction(
                row=0,
                channel=channel,
                sample_index=index,
                pitch=None,
                volume=None,
            )
        )

    def type_volume(self, volume: int, channel: Optional[ChannelName]) -> None:
        self.panel._handle_edit_action(
            EditAction(
                row=0,
                channel=channel,
                sample_index=None,
                pitch=None,
                volume=volume,
            )
        )

    def shown(self, channel: Optional[ChannelName]) -> str:
        """The label the cell cache holds, which is what the cell shows once the commit settles."""
        return self.panel._editable_cells.values.get((0, channel, SubColumn.VOICE), STORED_LABEL)

    def shown_pitch(self, channel: Optional[ChannelName]) -> str:
        """The pitch the cell cache holds, which is what the cell shows once the commit settles."""
        return self.panel._editable_cells.values.get((0, channel, SubColumn.TRANSPOSE), STORED_PITCH)

    def shown_volume(self, channel: Optional[ChannelName]) -> str:
        """The volume the cell cache holds, which is what the cell shows once the commit settles."""
        return self.panel._editable_cells.values.get((0, channel, SubColumn.VOLUME), STORED_VOLUME)

    def kind(self, channel: Optional[ChannelName]) -> Optional[VoiceKind]:
        """The kind the cell cache holds, which is the color the slot takes with its number."""
        return self.panel._cell_kinds.get((0, channel, SubColumn.VOICE))


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


class TestWhatColorATypedVoiceTakes:
    """The cell takes the kind with the number, so a typed voice reads whole before the project answers."""

    def test_a_typed_sample_takes_the_sample_kind(self, panel: Panel) -> None:
        panel.type_voice(SAMPLE_INDEX, ChannelName.PULSE1)

        assert panel.kind(ChannelName.PULSE1) is VoiceKind.SAMPLE

    def test_a_typed_instrument_takes_the_instrument_kind(self, panel: Panel) -> None:
        panel.type_voice(INSTRUMENT_INDEX, ChannelName.NOISE)

        assert panel.kind(ChannelName.NOISE) is VoiceKind.INSTRUMENT

    def test_a_refused_voice_leaves_the_cell_its_own_kind(self, panel: Panel) -> None:
        """Nothing is written, so the slot keeps the color it already wore."""
        panel.type_voice(INSTRUMENT_INDEX, None)

        assert panel.kind(None) is None

    def test_a_cut_cell_states_no_kind(self, panel: Panel) -> None:
        panel.panel.on_set_note_off = lambda row, channel: None
        panel.panel._handle_edit_action(
            EditAction(
                row=0,
                channel=ChannelName.TRIANGLE,
                sample_index=None,
                pitch=None,
                volume=None,
                note_off=True,
            )
        )

        assert panel.kind(ChannelName.TRIANGLE) is None


class TestTypingAnOffsetInTheSampleColumn:
    """The sample column takes a pitch or a volume on a row where a sample plays."""

    def test_a_volume_typed_where_no_sample_plays_leaves_the_cell_showing_what_it_held(
        self,
        panel: Panel,
    ) -> None:
        """The project would take nothing, so a cell taking the value optimistically would keep it."""
        panel.type_volume(TYPED_VOLUME, None)

        assert panel.writes == []
        assert panel.shown_volume(None) == STORED_VOLUME

    def test_a_volume_typed_where_a_sample_plays_is_written(self, panel: Panel) -> None:
        panel.panel._rows_taking_offsets = frozenset({0})

        panel.type_volume(TYPED_VOLUME, None)

        assert panel.offsets == [(0, None, None, TYPED_VOLUME)]
        assert panel.shown_volume(None) == display_volume(TYPED_VOLUME)

    def test_a_volume_typed_in_a_channel_column_is_written_where_no_sample_plays(
        self,
        panel: Panel,
    ) -> None:
        panel.type_volume(TYPED_VOLUME, ChannelName.PULSE1)

        assert panel.offsets == [(0, ChannelName.PULSE1, None, TYPED_VOLUME)]
        assert panel.shown_volume(ChannelName.PULSE1) == display_volume(TYPED_VOLUME)


class TestTypingAPitchWithAMarkedVoice:
    """A pitch typed while the voices list marks a voice places that voice too, where the column takes it."""

    def test_a_marked_sample_lands_with_the_pitch_in_a_channel_column(self, panel: Panel) -> None:
        panel.mark(SAMPLE_INDEX)

        panel.type_pitch(TYPED_NOTE, ChannelName.PULSE1)

        assert panel.writes == [(0, ChannelName.PULSE1, "lead-id")]
        assert panel.offsets == [(0, ChannelName.PULSE1, TYPED_NOTE, None)]
        assert panel.shown(ChannelName.PULSE1) == display_id(SAMPLE_INDEX)
        assert panel.kind(ChannelName.PULSE1) is VoiceKind.SAMPLE
        assert panel.shown_pitch(ChannelName.PULSE1) == display_pitch(TYPED_NOTE)

    def test_a_marked_instrument_lands_with_the_pitch_in_a_channel_column(self, panel: Panel) -> None:
        panel.mark(INSTRUMENT_INDEX)

        panel.type_pitch(TYPED_NOTE, ChannelName.NOISE)

        assert panel.writes == [(0, ChannelName.NOISE, "pad-id")]
        assert panel.kind(ChannelName.NOISE) is VoiceKind.INSTRUMENT

    def test_a_marked_sample_fills_the_sample_column_where_no_sample_plays(self, panel: Panel) -> None:
        """The sample spreads over its channels first, so the pitch has channels to land on."""
        panel.mark(SAMPLE_INDEX)

        panel.type_pitch(TYPED_NOTE, None)

        assert panel.writes == [(0, None, "lead-id")]
        assert panel.offsets == [(0, None, TYPED_NOTE, None)]
        assert panel.shown(None) == display_id(SAMPLE_INDEX)

    def test_a_marked_instrument_writes_the_pitch_alone_in_the_sample_column(self, panel: Panel) -> None:
        panel.panel._rows_taking_offsets = frozenset({0})
        panel.mark(INSTRUMENT_INDEX)

        panel.type_pitch(TYPED_NOTE, None)

        assert panel.writes == [(0, None, None)]
        assert panel.offsets == [(0, None, TYPED_NOTE, None)]
        assert panel.shown(None) == STORED_LABEL

    def test_a_marked_instrument_lands_nowhere_in_the_sample_column_without_a_sample(self, panel: Panel) -> None:
        panel.mark(INSTRUMENT_INDEX)

        panel.type_pitch(TYPED_NOTE, None)

        assert panel.writes == []
        assert panel.shown_pitch(None) == STORED_PITCH

    def test_without_a_mark_the_pitch_goes_alone(self, panel: Panel) -> None:
        panel.type_pitch(TYPED_NOTE, ChannelName.PULSE1)

        assert panel.writes == [(0, ChannelName.PULSE1, None)]
        assert panel.shown(ChannelName.PULSE1) == STORED_LABEL

    def test_a_volume_leaves_the_mark_out(self, panel: Panel) -> None:
        panel.mark(SAMPLE_INDEX)

        panel.type_volume(TYPED_VOLUME, ChannelName.PULSE1)

        assert panel.writes == [(0, ChannelName.PULSE1, None)]

    def test_a_typed_number_names_its_own_voice_over_the_mark(self, panel: Panel) -> None:
        panel.mark(SAMPLE_INDEX)

        panel.type_voice(INSTRUMENT_INDEX, ChannelName.PULSE1)

        assert panel.writes == [(0, ChannelName.PULSE1, "pad-id")]
