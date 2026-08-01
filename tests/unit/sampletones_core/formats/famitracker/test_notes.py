from dataclasses import dataclass
from typing import List

import pytest

from sampletones_core.formats.famitracker.notes import (
    period_to_note_cell,
    pitch_to_note_cell,
    resolve_machine,
)
from sampletones_core.formats.famitracker.specification.parameters import (
    ENGINE_SPEED_MACHINE_DEFAULT,
    Machine,
)


@dataclass
class NoteCase:
    pitch: int
    note: int
    octave: int


PITCH_CASES: List[NoteCase] = [
    NoteCase(pitch=24, note=1, octave=0),  # C-0, lowest representable
    NoteCase(pitch=33, note=10, octave=0),  # A-0
    NoteCase(pitch=60, note=1, octave=3),  # C-3
    NoteCase(pitch=119, note=12, octave=7),  # B-7, highest representable
    NoteCase(pitch=12, note=1, octave=0),  # below range clamps up to C-0
    NoteCase(pitch=200, note=12, octave=7),  # above range clamps down to B-7
]

PERIOD_CASES: List[NoteCase] = [
    NoteCase(pitch=0, note=1, octave=0),
    NoteCase(pitch=11, note=12, octave=0),
    NoteCase(pitch=15, note=4, octave=1),
    NoteCase(pitch=16, note=1, octave=0),  # wraps into the 16 noise periods
]


class TestPitchToNoteCell:
    @pytest.mark.parametrize("case", PITCH_CASES)
    def test_pitch_maps_to_note_and_octave(self, case: NoteCase) -> None:
        cell = pitch_to_note_cell(case.pitch)
        assert cell.note == case.note
        assert cell.octave == case.octave

    def test_octave_stays_within_range(self) -> None:
        for pitch in range(-50, 200):
            cell = pitch_to_note_cell(pitch)
            assert 0 <= cell.octave <= 7
            assert 1 <= cell.note <= 12


class TestPeriodToNoteCell:
    @pytest.mark.parametrize("case", PERIOD_CASES)
    def test_period_maps_to_note_and_octave(self, case: NoteCase) -> None:
        cell = period_to_note_cell(case.pitch)
        assert cell.note == case.note
        assert cell.octave == case.octave

    def test_note_and_octave_reduce_back_to_period(self) -> None:
        for period in range(16):
            cell = period_to_note_cell(period)
            reduced = (cell.octave * 12 + cell.note - 1) & 0x0F
            assert reduced == period


class TestResolveMachine:
    def test_ntsc_rate_selects_ntsc_default_engine(self) -> None:
        assert resolve_machine(60) == (Machine.NTSC, ENGINE_SPEED_MACHINE_DEFAULT)

    def test_pal_rate_selects_pal_default_engine(self) -> None:
        assert resolve_machine(50) == (Machine.PAL, ENGINE_SPEED_MACHINE_DEFAULT)

    def test_custom_rate_keeps_ntsc_and_carries_engine_speed(self) -> None:
        assert resolve_machine(30) == (Machine.NTSC, 30)
