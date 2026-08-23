from dataclasses import dataclass, field
from typing import Final, List, Optional, Tuple

import pytest

from sampletones_application.constants.tracker import DEFAULT_OCTAVE
from sampletones_application.ui.panels.sequencer.input.tracker import (
    TrackerCursor,
    TrackerInputState,
)
from sampletones_application.ui.panels.sequencer.tracker import GUISequencerTrackerPanel
from sampletones_application.utils.gui.keyboard.combination import KeyCombination
from sampletones_application.utils.gui.keyboard.event import KeyEvent
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import ChannelName
from sampletones_shared.constants.music import OCTAVE_OFFSET, OCTAVE_SEMITONES

ROW: Final[int] = 3
ROW_COUNT: Final[int] = 64

Typed = Tuple[int, ChannelName, int]


@dataclass
class PianoFixture:
    panel: GUISequencerTrackerPanel
    typed: List[Typed] = field(default_factory=list)
    states: List[TrackerInputState] = field(default_factory=list)


def _panel(
    monkeypatch: pytest.MonkeyPatch,
    channel: Optional[ChannelName],
    subcolumn: SubColumn = SubColumn.TRANSPOSE,
) -> PianoFixture:
    """A tracker panel carrying only the state the note path reads."""
    panel = GUISequencerTrackerPanel.__new__(GUISequencerTrackerPanel)
    panel._octave = DEFAULT_OCTAVE
    panel._current_row_count = ROW_COUNT
    panel._input_state = TrackerInputState(cursor=TrackerCursor(ROW, channel, subcolumn))

    fixture = PianoFixture(panel=panel)
    panel.on_note_typed = lambda row, target, pitch: fixture.typed.append((row, target, pitch))
    monkeypatch.setattr(panel, "_apply_state", fixture.states.append)
    return fixture


def _press(text: str) -> KeyEvent:
    combination = KeyCombination.parse(text)
    return KeyEvent(key=combination.key, modifiers=combination.modifiers)


def _pitch(octave: int, semitone: int) -> int:
    return (octave + OCTAVE_OFFSET) * OCTAVE_SEMITONES + semitone


class TestANoteKeyWritesTheNoteItNames:
    def test_the_bottom_row_opens_at_the_octave_in_force(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fixture = _panel(monkeypatch, ChannelName.PULSE1)

        assert fixture.panel._type_note(_press("Z")) is True
        assert fixture.typed == [(ROW, ChannelName.PULSE1, _pitch(DEFAULT_OCTAVE, 0))]

    def test_the_top_row_opens_an_octave_above_it(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fixture = _panel(monkeypatch, ChannelName.PULSE1)

        fixture.panel._type_note(_press("Q"))

        assert fixture.typed == [(ROW, ChannelName.PULSE1, _pitch(DEFAULT_OCTAVE + 1, 0))]

    def test_a_black_key_lands_a_semitone_above_the_white_one_below_it(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        fixture = _panel(monkeypatch, ChannelName.PULSE1)

        fixture.panel._type_note(_press("S"))

        assert fixture.typed == [(ROW, ChannelName.PULSE1, _pitch(DEFAULT_OCTAVE, 1))]

    def test_the_octave_in_force_moves_the_note(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fixture = _panel(monkeypatch, ChannelName.PULSE1)
        fixture.panel._octave = DEFAULT_OCTAVE - 1

        fixture.panel._type_note(_press("Z"))

        assert fixture.typed == [(ROW, ChannelName.PULSE1, _pitch(DEFAULT_OCTAVE - 1, 0))]

    def test_a_typed_note_steps_onto_the_next_row(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fixture = _panel(monkeypatch, ChannelName.PULSE1)

        fixture.panel._type_note(_press("Z"))

        assert fixture.states[-1].cursor is not None
        assert fixture.states[-1].cursor.row == ROW + 1


class TestWhereTheNoteKeysStayOut:
    def test_the_sample_column_keeps_its_own_face(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The column speaks for a whole sample, whose channels rest at pitches of their own."""
        fixture = _panel(monkeypatch, None)

        assert fixture.panel._type_note(_press("Z")) is False
        assert fixture.typed == []

    def test_the_noise_channel_keeps_its_hex_entry(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fixture = _panel(monkeypatch, ChannelName.NOISE)

        assert fixture.panel._type_note(_press("Z")) is False
        assert fixture.typed == []

    def test_another_subcolumn_keeps_its_own_keys(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fixture = _panel(monkeypatch, ChannelName.PULSE1, SubColumn.VOLUME)

        assert fixture.panel._type_note(_press("Z")) is False
        assert fixture.typed == []

    def test_a_key_no_note_stands_on_is_left_alone(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fixture = _panel(monkeypatch, ChannelName.PULSE1)

        assert fixture.panel._type_note(_press("K")) is False
        assert fixture.typed == []
