from collections import Counter
from typing import Final

import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, GeneratorClassName
from sampletones_core.instructions import NoiseInstruction, PulseInstruction, TriangleInstruction
from sampletones_shared.constants.music import OCTAVE_SEMITONES
from sampletones_tools.calibration.referee.notes import Note, NoteReader, pitch_counts, timbre_of

EIGHTH_DUTY: Final[int] = 0
QUARTER_DUTY: Final[int] = 1
HALF_DUTY: Final[int] = 2
THREE_QUARTERS_DUTY: Final[int] = 3


@pytest.fixture(name="reader", scope="module")
def reader_fixture() -> NoteReader:
    return NoteReader(Config())


def _pulse(pitch: int) -> PulseInstruction:
    return PulseInstruction(on=True, pitch=pitch, volume=12, duty_cycle=2)


class TestNoteReader:
    def test_a_pulse_sounds_the_note_it_names(self, reader: NoteReader) -> None:
        assert reader.note(ChannelName.PULSE1, _pulse(69)) == Note(GeneratorClassName.PULSE_GENERATOR, 69)

    def test_the_triangle_sounds_an_octave_under_the_note_it_names(self, reader: NoteReader) -> None:
        note = reader.note(ChannelName.TRIANGLE, TriangleInstruction(on=True, pitch=57))

        assert note == Note(GeneratorClassName.TRIANGLE_GENERATOR, 57 - OCTAVE_SEMITONES)

    def test_a_bend_leaves_the_note_it_bends(self, reader: NoteReader) -> None:
        bent = PulseInstruction(on=True, pitch=69, volume=12, duty_cycle=2, detune=3)

        assert reader.note(ChannelName.PULSE1, bent) == reader.note(ChannelName.PULSE1, _pulse(69))

    def test_silence_and_the_noise_sound_no_note(self, reader: NoteReader) -> None:
        silent = PulseInstruction(on=False, pitch=69, volume=0, duty_cycle=2)
        hiss = NoiseInstruction(on=True, period=6, volume=10, short=False)

        assert reader.note(ChannelName.PULSE1, silent) is None
        assert reader.note(ChannelName.NOISE, hiss) is None
        assert reader.note(ChannelName.PULSE2, None) is None

    def test_two_pulses_in_unison_sound_one_note(self, reader: NoteReader) -> None:
        notes = reader.notes({ChannelName.PULSE1: _pulse(64), ChannelName.PULSE2: _pulse(64)})

        assert notes == frozenset({Note(GeneratorClassName.PULSE_GENERATOR, 64)})

    def test_a_bass_on_a_pulse_sounds_the_pitch_the_triangle_writes(self, reader: NoteReader) -> None:
        on_triangle = reader.notes({ChannelName.TRIANGLE: TriangleInstruction(on=True, pitch=57)})
        on_pulse = reader.notes({ChannelName.PULSE1: _pulse(57 - OCTAVE_SEMITONES)})

        assert on_triangle != on_pulse
        assert pitch_counts(on_triangle) == pitch_counts(on_pulse)

    def test_a_frame_of_no_channel_sounds_no_note(self, reader: NoteReader) -> None:
        assert reader.notes({}) == frozenset()


class TestPitchCounts:
    def test_a_unison_across_kinds_counts_its_pitch_once_per_kind(self) -> None:
        on_both = frozenset(
            {Note(GeneratorClassName.PULSE_GENERATOR, 48), Note(GeneratorClassName.TRIANGLE_GENERATOR, 48)}
        )

        assert pitch_counts(on_both) == Counter({48: 2})

    def test_no_note_counts_no_pitch(self) -> None:
        assert not pitch_counts(frozenset())


class TestTimbreOf:
    def test_three_quarters_sounds_as_a_quarter(self) -> None:
        assert timbre_of(QUARTER_DUTY) == timbre_of(THREE_QUARTERS_DUTY)

    def test_every_other_duty_keeps_a_timbre_of_its_own(self) -> None:
        timbres = [timbre_of(duty_cycle) for duty_cycle in (EIGHTH_DUTY, QUARTER_DUTY, HALF_DUTY)]

        assert len(set(timbres)) == len(timbres)
