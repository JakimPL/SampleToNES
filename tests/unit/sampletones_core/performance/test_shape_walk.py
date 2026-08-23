from dataclasses import dataclass
from typing import Tuple

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters import CHANNEL_TO_EXPORTER_MAP
from sampletones_core.instructions import PulseInstruction
from sampletones_core.performance import song_instructions
from sampletones_core.project.voices.envelopes import ShapeEnvelopes
from sampletones_core.project.voices.loop import WHOLE_LOOP_POINT
from sampletones_core.project.voices.shape import Shape
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.performance import place_instrument, project_with_shape

ROWS_PER_PATTERN: int = 4
VOLUME: Tuple[int, ...] = (15, 10)
ARPEGGIO: Tuple[int, ...] = (0, 5)


def _shape(loop: bool = False) -> Shape:
    return Shape(
        name="lead",
        envelopes=ShapeEnvelopes(volume=VOLUME, arpeggio=ARPEGGIO, duty_cycle=(1,)),
        loop_point=WHOLE_LOOP_POINT if loop else None,
    )


def _resting(channel_name: ChannelName) -> object:
    return CHANNEL_TO_EXPORTER_MAP[channel_name].get_instruction_type().null_instruction()


class TestAShapeSoundsOnEveryChannel(BaseTestSuite):
    """A hand-written voice is placed on any channel, and the walk sounds the frames it makes there."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        channel_name: ChannelName

    test_cases = (
        TestCase(label=ChannelName.PULSE1.value, channel_name=ChannelName.PULSE1),
        TestCase(label=ChannelName.PULSE2.value, channel_name=ChannelName.PULSE2),
        TestCase(label=ChannelName.TRIANGLE.value, channel_name=ChannelName.TRIANGLE),
        TestCase(label=ChannelName.NOISE.value, channel_name=ChannelName.NOISE),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_walk_sounds_the_shape_where_it_was_placed(self, test_case: TestCase) -> None:
        shape = _shape()
        project = project_with_shape(shape, rows_per_pattern=ROWS_PER_PATTERN)
        place_instrument(
            project,
            channel_name=test_case.channel_name,
            row_index=0,
            sample=shape,
        )

        streams = song_instructions(project)

        assert streams[test_case.channel_name][: len(VOLUME)] == shape.instructions(test_case.channel_name)

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_channels_it_was_not_placed_on_rest(self, test_case: TestCase) -> None:
        shape = _shape()
        project = project_with_shape(shape, rows_per_pattern=ROWS_PER_PATTERN)
        place_instrument(
            project,
            channel_name=test_case.channel_name,
            row_index=0,
            sample=shape,
        )

        streams = song_instructions(project)

        for channel_name in ChannelName.items():
            if channel_name is test_case.channel_name:
                continue

            assert set(streams[channel_name]) == {_resting(channel_name)}


class TestAShapeInASong:
    def test_a_one_shot_falls_silent_past_its_envelopes(self) -> None:
        shape = _shape()
        project = project_with_shape(shape, rows_per_pattern=ROWS_PER_PATTERN)
        place_instrument(project, channel_name=ChannelName.PULSE1, row_index=0, sample=shape)

        stream = song_instructions(project)[ChannelName.PULSE1]

        assert stream[len(VOLUME) :] == [_resting(ChannelName.PULSE1)] * (len(stream) - len(VOLUME))

    def test_a_looping_shape_keeps_sounding(self) -> None:
        shape = _shape(loop=True)
        project = project_with_shape(shape, rows_per_pattern=ROWS_PER_PATTERN)
        place_instrument(project, channel_name=ChannelName.PULSE1, row_index=0, sample=shape)

        stream = song_instructions(project)[ChannelName.PULSE1]

        assert _resting(ChannelName.PULSE1) not in stream

    def test_a_rows_transpose_bends_the_shape_off_its_root(self) -> None:
        shape = _shape()
        project = project_with_shape(shape, rows_per_pattern=ROWS_PER_PATTERN)
        place_instrument(
            project,
            channel_name=ChannelName.PULSE1,
            row_index=0,
            sample=shape,
            transpose=7,
        )

        first = song_instructions(project)[ChannelName.PULSE1][0]

        assert isinstance(first, PulseInstruction)
        assert first.pitch == shape.root_pitch + ARPEGGIO[0] + 7
