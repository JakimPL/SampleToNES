from typing import Final, List, Tuple

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.formats.famitracker.builder import build_instrument_table, project_to_module
from sampletones_core.formats.famitracker.model.pattern import PatternData
from sampletones_core.formats.famitracker.notes import period_to_note_cell, pitch_to_note_cell
from sampletones_core.formats.famitracker.specification.channels import CHANNEL_TO_ID
from sampletones_core.formats.famitracker.specification.sequences import (
    LOOP_FROM_START,
    NO_LOOP_POINT,
    SequenceKind,
)
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.project import Project
from sampletones_core.project.voices.envelopes import ShapeEnvelopes
from sampletones_core.project.voices.note_on import NoteOn
from sampletones_core.project.voices.shape import Shape

ROWS_PER_PATTERN: Final[int] = 4
VOLUME: Final[Tuple[int, ...]] = (15, 12, 9)
ARPEGGIO: Final[Tuple[int, ...]] = (0, 4, 7)
DUTY_CYCLE: Final[Tuple[int, ...]] = (2,)
TAIL_LOOP_POINT: Final[int] = 1
TRANSPOSE: Final[int] = 5


def _shape(loop_point: int | None = None) -> Shape:
    return Shape(
        name="Lead",
        envelopes=ShapeEnvelopes(volume=VOLUME, arpeggio=ARPEGGIO, duty_cycle=DUTY_CYCLE),
        loop_point=loop_point,
    )


def _project(shape: Shape, *channels: ChannelName, transpose: int = 0) -> Project:
    project = Project.create(title="Demo", rows_per_pattern=ROWS_PER_PATTERN)
    project.voices.append(shape)
    for channel in channels:
        pattern = project.song[channel].ensure_pattern(0, ROWS_PER_PATTERN)
        pattern.rows[0] = Row(command=NoteOn(voice_id=shape.id), transpose=transpose)
        project.song.set_order_entry(0, channel, 0)

    return project


def _rows(patterns: List[PatternData], channel: ChannelName) -> List[object]:
    return [row for pattern in patterns if pattern.channel == CHANNEL_TO_ID[channel] for row in pattern.rows]


class TestAShapeReachesTheModule:
    def test_a_shape_used_on_several_channels_is_written_once(self) -> None:
        shape = _shape()
        project = _project(shape, ChannelName.PULSE1, ChannelName.PULSE2, ChannelName.NOISE)

        instruments, slots = build_instrument_table(project)

        assert len(instruments) == 1
        assert instruments[0].name == "Lead"
        assert {slots[(shape.id, channel)].index for channel in ChannelName.items()} == {0}

    def test_the_instrument_carries_every_dimension_the_shape_writes(self) -> None:
        instruments, _ = build_instrument_table(_project(_shape(), ChannelName.PULSE1))

        sequences = instruments[0].sequences
        assert sequences[SequenceKind.VOLUME].items == VOLUME
        assert sequences[SequenceKind.ARPEGGIO].items == ARPEGGIO
        assert sequences[SequenceKind.DUTY].items == DUTY_CYCLE * len(VOLUME)

    def test_a_one_shot_leaves_every_loop_point_unset(self) -> None:
        instruments, _ = build_instrument_table(_project(_shape(), ChannelName.PULSE1))

        assert all(sequence.loop_point == NO_LOOP_POINT for sequence in instruments[0].sequences.values())

    def test_a_loop_point_reaches_every_populated_sequence(self) -> None:
        instruments, _ = build_instrument_table(_project(_shape(TAIL_LOOP_POINT), ChannelName.PULSE1))

        populated = [sequence for sequence in instruments[0].sequences.values() if sequence.items]
        assert [sequence.loop_point for sequence in populated] == [TAIL_LOOP_POINT] * len(populated)

    def test_a_shorter_dimension_runs_the_length_of_the_longest(self) -> None:
        """A tracker advances each sequence on its own counter, so they must share a length."""
        shape = Shape(
            name="Lead",
            envelopes=ShapeEnvelopes(volume=VOLUME, duty_cycle=DUTY_CYCLE),
            loop_point=TAIL_LOOP_POINT,
        )
        instruments, _ = build_instrument_table(_project(shape, ChannelName.PULSE1))

        duty = instruments[0].sequences[SequenceKind.DUTY]
        assert duty.items == DUTY_CYCLE * len(VOLUME)
        assert duty.loop_point == TAIL_LOOP_POINT

    def test_a_looping_shape_still_repeats_from_the_start(self) -> None:
        instruments, _ = build_instrument_table(_project(_shape(LOOP_FROM_START), ChannelName.PULSE1))

        populated = [sequence for sequence in instruments[0].sequences.values() if sequence.items]
        assert all(sequence.loop_point == LOOP_FROM_START for sequence in populated)


class TestTheRowsNameTheShapesRoot:
    @pytest.mark.parametrize(
        "channel",
        [ChannelName.PULSE1, ChannelName.PULSE2, ChannelName.TRIANGLE],
    )
    def test_a_tonal_row_states_the_root_moved_by_its_transpose(self, channel: ChannelName) -> None:
        shape = _shape()
        module = project_to_module(_project(shape, channel, transpose=TRANSPOSE))

        cell = pitch_to_note_cell(shape.root_pitch + TRANSPOSE)
        row = _rows(list(module.track.patterns), channel)[0]
        assert (row.note, row.octave) == (cell.note, cell.octave)

    def test_a_noise_row_states_the_period_root_moved_by_its_transpose(self) -> None:
        shape = _shape()
        module = project_to_module(_project(shape, ChannelName.NOISE, transpose=TRANSPOSE))

        cell = period_to_note_cell(shape.root_period + TRANSPOSE)
        row = _rows(list(module.track.patterns), ChannelName.NOISE)[0]
        assert (row.note, row.octave) == (cell.note, cell.octave)

    def test_every_channel_names_the_one_instrument(self) -> None:
        shape = _shape()
        module = project_to_module(_project(shape, *ChannelName.items()))

        for channel in ChannelName.items():
            assert _rows(list(module.track.patterns), channel)[0].instrument == 0
