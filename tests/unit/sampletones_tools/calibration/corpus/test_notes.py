from collections import Counter
from typing import Final, List

import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_PERIOD
from sampletones_core.instructions import NoiseInstruction, PulseInstruction
from sampletones_tools.calibration.config.notes import NotesConfig
from sampletones_tools.calibration.corpus.item import CorpusItem
from sampletones_tools.calibration.corpus.notes import NOISE_CATEGORY, PULSE_CATEGORY, TRIANGLE_CATEGORY, build_notes

GRID: Final[NotesConfig] = NotesConfig(
    first_pitch=33,
    last_pitch=43,
    pitch_step=5,
    volumes=[15, 1],
    duty_cycles=[0],
    alternating_duty_cycles=[1, 3],
    sounding_frames=3,
    silent_frames=2,
    listed_pitch_stride=2,
    listed_noise_period_stride=8,
)


@pytest.fixture(name="notes", scope="module")
def notes_fixture() -> List[CorpusItem]:
    return build_notes(Config(), grid=GRID)


def _pulse(item: CorpusItem) -> PulseInstruction:
    assert item.truth is not None
    frame = item.truth.instructions[ChannelName.PULSE1][0]
    assert isinstance(frame, PulseInstruction)
    return frame


class TestBuildNotes:
    def test_every_channel_sounds_its_whole_grid(self, notes: List[CorpusItem]) -> None:
        counts = Counter(item.category for item in notes)

        assert counts[PULSE_CATEGORY] == len(GRID.pitches) * 2 * len(GRID.volumes)
        assert counts[TRIANGLE_CATEGORY] == len(GRID.pitches)
        assert counts[NOISE_CATEGORY] == (MAX_PERIOD + 1) * 2 * len(GRID.volumes)

    def test_the_alternating_duty_cycles_join_the_pitches_in_turn(self, notes: List[CorpusItem]) -> None:
        alternating = {
            _pulse(item).pitch: _pulse(item).duty_cycle
            for item in notes
            if item.category == PULSE_CATEGORY and _pulse(item).duty_cycle != 0
        }

        assert alternating == {33: 1, 38: 3, 43: 1}

    def test_a_note_holds_then_falls_silent(self, notes: List[CorpusItem]) -> None:
        truth = notes[0].truth
        assert truth is not None

        assert [frame.on for frame in truth.instructions[ChannelName.PULSE1]] == [True] * 3 + [False] * 2

    def test_the_page_lists_the_loudest_notes_at_every_stride(self, notes: List[CorpusItem]) -> None:
        listed_noise = [item for item in notes if item.category == NOISE_CATEGORY and item.listed]
        listed_pulse = [_pulse(item) for item in notes if item.category == PULSE_CATEGORY and item.listed]

        assert {frame.pitch for frame in listed_pulse} == {33, 43}
        assert {frame.volume for frame in listed_pulse} == {15}
        assert len(listed_noise) == 2 * len(range(0, MAX_PERIOD + 1, 8))
        for item in listed_noise:
            assert item.truth is not None
            frame = item.truth.instructions[ChannelName.NOISE][0]
            assert isinstance(frame, NoiseInstruction) and frame.volume == 15

    def test_names_stay_unique(self, notes: List[CorpusItem]) -> None:
        names = [item.name for item in notes]

        assert len(names) == len(set(names))

    def test_the_page_lists_a_triangle_note_at_every_stride(self, notes: List[CorpusItem]) -> None:
        listed = [item.name for item in notes if item.category == TRIANGLE_CATEGORY and item.listed]

        assert listed == [f"note-triangle-p{pitch}" for pitch in GRID.pitches[:: GRID.listed_pitch_stride]]

    def test_the_noise_sounds_its_long_mode_first(self, notes: List[CorpusItem]) -> None:
        modes = [item.name.split("-")[2] for item in notes if item.category == NOISE_CATEGORY]

        assert modes == ["long"] * (len(modes) // 2) + ["short"] * (len(modes) // 2)


class TestFixedDutyCyclesAlone:
    def test_a_grid_of_no_alternating_duty_cycles_sounds_its_fixed_ones_alone(self) -> None:
        grid = GRID.model_copy(update={"duty_cycles": [0, 2], "alternating_duty_cycles": []})

        pulses = [_pulse(item) for item in build_notes(Config(), grid=grid) if item.category == PULSE_CATEGORY]

        assert Counter(frame.duty_cycle for frame in pulses) == {
            0: len(GRID.pitches) * len(GRID.volumes),
            2: len(GRID.pitches) * len(GRID.volumes),
        }
