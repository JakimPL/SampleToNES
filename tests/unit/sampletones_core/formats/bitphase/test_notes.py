from dataclasses import dataclass
from typing import Final

import pytest

from sampletones_core.constants.general import NUM_PERIODS
from sampletones_core.formats.bitphase.notes import (
    noise_arpeggio_to_table_offset,
    noise_period_to_note_index,
    note_index_to_note_cell,
    pitch_to_note_index,
)
from sampletones_core.formats.bitphase.specification.chip import TUNING_TABLE_LENGTH
from sampletones_core.formats.bitphase.specification.patterns import (
    FIRST_OCTAVE,
    MAX_NOTE_INDEX,
    MIN_NOTE_INDEX,
    NOTE_INDEX_PITCH_OFFSET,
    NOTE_RANGE,
    NoteName,
)
from tests.suite.case import BaseRegularTestCase

LOWEST_STEP: Final[int] = -NUM_PERIODS
HIGHEST_STEP: Final[int] = NUM_PERIODS


def bitphase_note_value(name: int, octave: int) -> int:
    """The note index Bitphase's pattern processor reads back from a note cell."""
    return name - int(NoteName.C) + (octave - FIRST_OCTAVE) * NOTE_RANGE


def bitphase_noise_period(index: int) -> int:
    """The noise period Bitphase's playback selects for a note index."""
    return NUM_PERIODS - 1 - index % NUM_PERIODS


class TestPitchToNoteIndex:
    @dataclass(frozen=True, kw_only=True)
    class PitchCase(BaseRegularTestCase):
        pitch: int
        index: int

    test_cases = (
        PitchCase(pitch=24, index=0, label="24"),
        PitchCase(pitch=60, index=36, label="60"),
        PitchCase(pitch=119, index=95, label="119"),
        PitchCase(pitch=0, index=0, label="0"),
        PitchCase(pitch=200, index=95, label="200"),
    )

    @pytest.mark.parametrize("case", test_cases, ids=lambda case: case.label)
    def test_a_pitch_lands_on_its_tuning_table_index(self, case: PitchCase) -> None:
        assert pitch_to_note_index(case.pitch) == case.index

    def test_every_pitch_lands_inside_the_tuning_table(self) -> None:
        indices = [pitch_to_note_index(pitch) for pitch in range(-50, 200)]
        assert all(MIN_NOTE_INDEX <= index <= MAX_NOTE_INDEX for index in indices)

    def test_the_playable_span_keeps_its_distance_from_the_pitch(self) -> None:
        pitches = range(NOTE_INDEX_PITCH_OFFSET, NOTE_INDEX_PITCH_OFFSET + TUNING_TABLE_LENGTH)
        assert all(pitch_to_note_index(pitch) == pitch - NOTE_INDEX_PITCH_OFFSET for pitch in pitches)


class TestNoteIndexToNoteCell:
    @dataclass(frozen=True, kw_only=True)
    class NoteCellCase(BaseRegularTestCase):
        index: int
        name: int
        octave: int

    test_cases = (
        NoteCellCase(index=0, name=int(NoteName.C), octave=1, label="0"),
        NoteCellCase(index=36, name=int(NoteName.C), octave=4, label="36"),
        NoteCellCase(index=45, name=11, octave=4, label="45"),
        NoteCellCase(index=95, name=int(NoteName.B), octave=8, label="95"),
    )

    @pytest.mark.parametrize("case", test_cases, ids=lambda case: case.label)
    def test_an_index_names_a_semitone_and_an_octave(self, case: NoteCellCase) -> None:
        cell = note_index_to_note_cell(case.index)
        assert (cell.name, cell.octave) == (case.name, case.octave)

    def test_bitphase_reads_the_written_index_back(self) -> None:
        """Playback resolves a cell to ``name - 2 + (octave - 1) * 12``, which is the
        index the tuning table is read at, so the round trip is the note's contract.
        """
        for index in range(TUNING_TABLE_LENGTH):
            cell = note_index_to_note_cell(index)
            assert bitphase_note_value(cell.name, cell.octave) == index

    def test_every_cell_names_a_pitched_semitone(self) -> None:
        cells = [note_index_to_note_cell(index) for index in range(TUNING_TABLE_LENGTH)]
        assert all(int(NoteName.C) <= cell.name <= int(NoteName.B) for cell in cells)


class TestNoisePeriods:
    @pytest.mark.parametrize("period", range(NUM_PERIODS))
    def test_a_period_reaches_the_note_index_that_selects_it(self, period: int) -> None:
        assert bitphase_noise_period(noise_period_to_note_index(period)) == period

    @pytest.mark.parametrize("period", range(NUM_PERIODS))
    def test_a_base_note_leaves_a_whole_cycle_of_offsets_playable(self, period: int) -> None:
        index = noise_period_to_note_index(period)
        assert MIN_NOTE_INDEX <= index <= MAX_NOTE_INDEX - (NUM_PERIODS - 1)

    @pytest.mark.parametrize("step", range(LOWEST_STEP, HIGHEST_STEP + 1))
    def test_an_arpeggio_step_moves_the_period_by_that_much(self, step: int) -> None:
        """The table offset and the base note together reproduce the period the
        reconstruction chose, wrapped into the sixteen the channel holds.
        """
        for period in range(NUM_PERIODS):
            index = noise_period_to_note_index(period) + noise_arpeggio_to_table_offset(step)
            assert bitphase_noise_period(index) == (period + step) % NUM_PERIODS

    @pytest.mark.parametrize("step", range(LOWEST_STEP, HIGHEST_STEP + 1))
    def test_every_reached_note_stays_inside_the_tuning_table(self, step: int) -> None:
        offset = noise_arpeggio_to_table_offset(step)
        indices = [noise_period_to_note_index(period) + offset for period in range(NUM_PERIODS)]
        assert all(MIN_NOTE_INDEX <= index <= MAX_NOTE_INDEX for index in indices)
