from dataclasses import dataclass
from typing import Tuple

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters import CHANNEL_TO_EXPORTER_MAP
from sampletones_core.instructions import PulseInstruction
from sampletones_core.performance import song_instructions
from sampletones_core.project.voices.envelopes import InstrumentEnvelopes
from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.project.voices.loop import WHOLE_LOOP_POINT
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.performance import place_instrument, project_with_instrument

ROWS_PER_PATTERN: int = 4
VOLUME: Tuple[int, ...] = (15, 10)
ARPEGGIO: Tuple[int, ...] = (0, 5)


def _instrument(loop: bool = False) -> Instrument:
    return Instrument(
        name="lead",
        envelopes=InstrumentEnvelopes(volume=VOLUME, arpeggio=ARPEGGIO, duty_cycle=(1,)),
        loop_point=WHOLE_LOOP_POINT if loop else None,
    )


def _resting(channel_name: ChannelName) -> object:
    return CHANNEL_TO_EXPORTER_MAP[channel_name].get_instruction_type().null_instruction()


class TestAnInstrumentSoundsOnEveryChannel(BaseTestSuite):
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
    def test_the_walk_sounds_the_instrument_where_it_was_placed(self, test_case: TestCase) -> None:
        instrument = _instrument()
        project = project_with_instrument(instrument, rows_per_pattern=ROWS_PER_PATTERN)
        place_instrument(
            project,
            channel_name=test_case.channel_name,
            row_index=0,
            sample=instrument,
        )

        streams = song_instructions(project)

        assert streams[test_case.channel_name][: len(VOLUME)] == instrument.instructions(test_case.channel_name)

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_channels_it_was_not_placed_on_rest(self, test_case: TestCase) -> None:
        instrument = _instrument()
        project = project_with_instrument(instrument, rows_per_pattern=ROWS_PER_PATTERN)
        place_instrument(
            project,
            channel_name=test_case.channel_name,
            row_index=0,
            sample=instrument,
        )

        streams = song_instructions(project)

        for channel_name in ChannelName.items():
            if channel_name is test_case.channel_name:
                continue

            assert set(streams[channel_name]) == {_resting(channel_name)}


class TestAnInstrumentInASong:
    def test_a_one_shot_falls_silent_past_its_envelopes(self) -> None:
        instrument = _instrument()
        project = project_with_instrument(instrument, rows_per_pattern=ROWS_PER_PATTERN)
        place_instrument(project, channel_name=ChannelName.PULSE1, row_index=0, sample=instrument)

        stream = song_instructions(project)[ChannelName.PULSE1]

        assert stream[len(VOLUME) :] == [_resting(ChannelName.PULSE1)] * (len(stream) - len(VOLUME))

    def test_a_looping_instrument_keeps_sounding(self) -> None:
        instrument = _instrument(loop=True)
        project = project_with_instrument(instrument, rows_per_pattern=ROWS_PER_PATTERN)
        place_instrument(project, channel_name=ChannelName.PULSE1, row_index=0, sample=instrument)

        stream = song_instructions(project)[ChannelName.PULSE1]

        assert _resting(ChannelName.PULSE1) not in stream

    def test_a_rows_transpose_bends_the_instrument_off_its_root(self) -> None:
        instrument = _instrument()
        project = project_with_instrument(instrument, rows_per_pattern=ROWS_PER_PATTERN)
        place_instrument(
            project,
            channel_name=ChannelName.PULSE1,
            row_index=0,
            sample=instrument,
            transpose=7,
        )

        first = song_instructions(project)[ChannelName.PULSE1][0]

        assert isinstance(first, PulseInstruction)
        assert first.pitch == instrument.root_pitch + ARPEGGIO[0] + 7
