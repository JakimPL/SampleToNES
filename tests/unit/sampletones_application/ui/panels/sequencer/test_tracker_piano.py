from dataclasses import dataclass, field
from typing import Final, List, Optional

import pytest

from sampletones_application.constants.tracker import DEFAULT_OCTAVE
from sampletones_application.ui.panels.sequencer.input.edit import EditAction
from sampletones_application.ui.panels.sequencer.input.tracker import (
    TrackerCursor,
    TrackerInputState,
)
from sampletones_application.ui.panels.sequencer.tracker.band import TrackerRows
from sampletones_application.ui.panels.sequencer.tracker.panel import GUISequencerTrackerPanel
from sampletones_application.utils.gui.keyboard.combination import KeyCombination
from sampletones_application.utils.gui.keyboard.event import KeyEvent
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_application.view_model.sequencer.tracker import NO_REACH
from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_PITCH, NUM_PERIODS
from sampletones_core.project.patterns.pitch import Note
from sampletones_shared.constants.music import OCTAVE_OFFSET, OCTAVE_SEMITONES

ROW: Final[int] = 3
ROW_COUNT: Final[int] = 64
TOP_OCTAVE: Final[int] = 7


@dataclass
class PianoFixture:
    panel: GUISequencerTrackerPanel
    actions: List[EditAction] = field(default_factory=list)
    states: List[TrackerInputState] = field(default_factory=list)


def _panel(
    monkeypatch: pytest.MonkeyPatch,
    channel: Optional[ChannelName],
    subcolumn: SubColumn = SubColumn.TRANSPOSE,
) -> PianoFixture:
    """A tracker panel carrying only the state the note path reads, its edits recorded in place of committed."""
    panel = GUISequencerTrackerPanel.__new__(GUISequencerTrackerPanel)
    panel._octave = DEFAULT_OCTAVE
    panel._rows_layout = TrackerRows(reach=NO_REACH, frame_rows=ROW_COUNT)
    panel._input_state = TrackerInputState(cursor=TrackerCursor(ROW, channel, subcolumn))

    fixture = PianoFixture(panel=panel)
    monkeypatch.setattr(panel, "_handle_edit_action", fixture.actions.append)
    monkeypatch.setattr(panel, "_apply_state", fixture.states.append)
    return fixture


def _press(text: str) -> KeyEvent:
    combination = KeyCombination.parse(text)
    return KeyEvent(key=combination.key, modifiers=combination.modifiers)


def _pitch(octave: int, semitone: int) -> int:
    return (octave + OCTAVE_OFFSET) * OCTAVE_SEMITONES + semitone


def _typed(channel: Optional[ChannelName], note: Note) -> EditAction:
    return EditAction(row=ROW, channel=channel, sample_index=None, pitch=note, volume=None)


class TestANoteKeyWritesTheNoteItNames:
    def test_the_bottom_row_opens_at_the_octave_in_force(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fixture = _panel(monkeypatch, ChannelName.PULSE1)

        assert fixture.panel._type_note(_press("Z")) is True
        assert fixture.actions == [_typed(ChannelName.PULSE1, Note(value=_pitch(DEFAULT_OCTAVE, 0)))]

    def test_the_top_row_opens_an_octave_above_it(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fixture = _panel(monkeypatch, ChannelName.PULSE1)

        fixture.panel._type_note(_press("Q"))

        assert fixture.actions == [_typed(ChannelName.PULSE1, Note(value=_pitch(DEFAULT_OCTAVE + 1, 0)))]

    def test_the_top_rows_white_keys_skip_the_black_ones(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fixture = _panel(monkeypatch, ChannelName.PULSE1)

        fixture.panel._type_note(_press("W"))

        assert fixture.actions == [_typed(ChannelName.PULSE1, Note(value=_pitch(DEFAULT_OCTAVE + 1, 2)))]

    def test_a_black_key_lands_a_semitone_above_the_white_one_below_it(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        fixture = _panel(monkeypatch, ChannelName.PULSE1)

        fixture.panel._type_note(_press("S"))

        assert fixture.actions == [_typed(ChannelName.PULSE1, Note(value=_pitch(DEFAULT_OCTAVE, 1)))]

    def test_the_octave_in_force_moves_the_note(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fixture = _panel(monkeypatch, ChannelName.PULSE1)
        fixture.panel._octave = DEFAULT_OCTAVE - 1

        fixture.panel._type_note(_press("Z"))

        assert fixture.actions == [_typed(ChannelName.PULSE1, Note(value=_pitch(DEFAULT_OCTAVE - 1, 0)))]

    def test_a_note_above_the_highest_is_held_at_it(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fixture = _panel(monkeypatch, ChannelName.PULSE1)
        fixture.panel._octave = TOP_OCTAVE

        fixture.panel._type_note(_press("U"))

        assert fixture.actions == [_typed(ChannelName.PULSE1, Note(value=MAX_PITCH))]

    def test_a_typed_note_steps_onto_the_next_row(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fixture = _panel(monkeypatch, ChannelName.PULSE1)

        fixture.panel._type_note(_press("Z"))

        assert fixture.states[-1].cursor is not None
        assert fixture.states[-1].cursor.row == ROW + 1


class TestWhereTheNoteLands:
    """A note reaches every column: the noise channel takes it as a period, and the sample column as
    the pitch it names, which each channel the column reaches reads its own way.
    """

    def test_the_noise_channel_takes_the_period_the_pitch_names(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fixture = _panel(monkeypatch, ChannelName.NOISE)

        assert fixture.panel._type_note(_press("S")) is True
        assert fixture.actions == [
            _typed(ChannelName.NOISE, Note(value=_pitch(DEFAULT_OCTAVE, 1) % NUM_PERIODS)),
        ]

    def test_the_sample_column_takes_the_pitch(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fixture = _panel(monkeypatch, None)

        assert fixture.panel._type_note(_press("Z")) is True
        assert fixture.actions == [_typed(None, Note(value=_pitch(DEFAULT_OCTAVE, 0)))]


class TestWhereTheNoteKeysStayOut:
    def test_another_subcolumn_keeps_its_own_keys(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fixture = _panel(monkeypatch, ChannelName.PULSE1, SubColumn.VOLUME)

        assert fixture.panel._type_note(_press("Z")) is False
        assert fixture.actions == []

    def test_a_digit_types_a_step_and_no_note(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fixture = _panel(monkeypatch, ChannelName.PULSE1)

        assert fixture.panel._type_note(_press("2")) is False
        assert fixture.actions == []

    def test_a_key_no_note_stands_on_is_left_alone(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fixture = _panel(monkeypatch, ChannelName.PULSE1)

        assert fixture.panel._type_note(_press("K")) is False
        assert fixture.actions == []

    @pytest.mark.parametrize("written", ["Ctrl+Z", "Alt+Z", "Super+Z"])
    def test_a_combination_ending_in_a_note_key_is_left_to_the_shortcuts(
        self,
        monkeypatch: pytest.MonkeyPatch,
        written: str,
    ) -> None:
        fixture = _panel(monkeypatch, ChannelName.PULSE1)

        assert fixture.panel._type_note(_press(written)) is False
        assert fixture.actions == []

    def test_a_note_key_under_shift_types_its_note(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fixture = _panel(monkeypatch, ChannelName.PULSE1)

        assert fixture.panel._type_note(_press("Shift+Z")) is True
        assert fixture.actions == [_typed(ChannelName.PULSE1, Note(value=_pitch(DEFAULT_OCTAVE, 0)))]
