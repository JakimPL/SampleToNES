from typing import Final, List

from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import InstructionUnion, PulseInstruction, TriangleInstruction
from sampletones_tools.calibration.corpus.truth import PitchLine
from sampletones_tools.calibration.referee.frames import channel_streams, common_length, line_within, sounds

LEAD: Final[InstructionUnion] = PulseInstruction(on=True, pitch=69, volume=12, duty_cycle=2)
REST: Final[InstructionUnion] = PulseInstruction(on=False, pitch=69, volume=0, duty_cycle=2)
BASS: Final[InstructionUnion] = TriangleInstruction(on=True, pitch=45)
MELODY: Final[List[InstructionUnion]] = [LEAD, REST, LEAD, LEAD]
LINE: Final[PitchLine] = (110.0, None, 220.0, 220.0)


class TestChannelStreams:
    def test_every_channel_is_cut_to_the_length_and_a_missing_one_reads_as_silent(self) -> None:
        streams = channel_streams({ChannelName.PULSE1: MELODY, ChannelName.TRIANGLE: []}, 3)

        assert list(streams) == ChannelName.items()
        assert streams[ChannelName.PULSE1] == tuple(MELODY[:3])
        assert streams[ChannelName.TRIANGLE] == (None, None, None)
        assert streams[ChannelName.NOISE] == (None, None, None)

    def test_a_length_of_zero_holds_no_frame(self) -> None:
        assert all(not stream for stream in channel_streams({ChannelName.PULSE1: MELODY}, 0).values())


class TestCommonLength:
    def test_the_shortest_stream_describing_frames_sets_the_length(self) -> None:
        assert common_length(MELODY, [BASS] * 2, MELODY) == 2

    def test_an_empty_stream_leaves_the_length_to_the_others(self) -> None:
        assert common_length([], MELODY) == len(MELODY)

    def test_no_stream_describing_frames_holds_no_frame(self) -> None:
        assert common_length() == 0
        assert common_length([], ()) == 0


class TestLineWithin:
    def test_a_line_is_cut_to_the_frames_the_conversion_plays(self) -> None:
        assert line_within(LINE, [(110.0, 110.0), (None, None, None)]) == LINE[:2]

    def test_a_line_shorter_than_the_conversion_is_read_whole(self) -> None:
        assert line_within(LINE[:2], [(110.0,) * len(LINE)]) == LINE[:2]

    def test_a_line_beside_no_played_line_is_read_whole(self) -> None:
        assert line_within(LINE, []) == LINE

    def test_an_empty_line_beside_a_sounding_conversion_holds_no_frame(self) -> None:
        assert line_within((), [(110.0,) * len(LINE)]) == ()


class TestSounds:
    def test_a_frame_sounds_where_it_is_on(self) -> None:
        assert sounds(LEAD)
        assert not sounds(REST)
        assert not sounds(None)
