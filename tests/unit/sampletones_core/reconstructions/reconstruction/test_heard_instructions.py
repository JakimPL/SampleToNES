from typing import Dict, Final, List, Sequence, Tuple

from sampletones_core.constants.algorithm import AUTHORED_STEM_ID, RESTING_STEM_ID
from sampletones_core.constants.enums import ChannelName, bending_channels
from sampletones_core.instructions import InstructionUnion, PulseInstruction
from sampletones_core.reconstructions.reconstruction.stems.channel_assignment import ChannelAssignment
from sampletones_core.reconstructions.reconstruction.stems.data import StemsData
from sampletones_core.reconstructions.reconstruction.stems.filter import heard_instructions
from sampletones_core.reconstructions.reconstruction.stems.selection import StemSelection
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings

STEM_A: Final[int] = 0
STEM_B: Final[int] = 1
EVERY_CHANNEL: Final[Tuple[ChannelName, ...]] = tuple(ChannelName.items())
CHANNEL: Final[ChannelName] = ChannelName.PULSE1


def _pulse(pitch: int) -> PulseInstruction:
    return PulseInstruction(on=True, pitch=pitch, volume=8, duty_cycle=0)


def _silence() -> PulseInstruction:
    return PulseInstruction.null_instruction()


def _heard(*stem_ids: int) -> StemSelection:
    return StemSelection.everywhere(frozenset(stem_ids), EVERY_CHANNEL)


def _stems_data(stem_ids: List[int]) -> StemsData:
    entries = [
        StemEntry(
            id=stem_id,
            settings=StemSettings(channels=[CHANNEL], bends=bending_channels([CHANNEL])),
        )
        for stem_id in (STEM_A, STEM_B)
    ]
    return StemsData(
        config=StemsConfig(
            entries=entries,
            hierarchy=StemsHierarchy(levels=[[entry.id] for entry in entries]),
        ),
        assignments=[ChannelAssignment(channel_name=CHANNEL, stem_ids=stem_ids)],
    )


def _reading(
    stream: Sequence[InstructionUnion],
    stem_ids: List[int],
    selection: StemSelection,
) -> List[InstructionUnion]:
    instructions: Dict[ChannelName, Sequence[InstructionUnion]] = {CHANNEL: stream}
    return heard_instructions(_stems_data(stem_ids), instructions, selection)[CHANNEL]


class TestWhatTheReadingLeavesOut:
    """A frame of a recording the reader left out states silence where it stands."""

    def test_a_frame_of_an_unheard_recording_reads_silent(self) -> None:
        reading = _reading(
            [_pulse(60), _pulse(62), _pulse(64)],
            [STEM_A, STEM_B, STEM_A],
            _heard(STEM_A),
        )

        assert reading == [_pulse(60), _silence(), _pulse(64)]

    def test_a_frame_of_a_heard_recording_reads_as_it_plays(self) -> None:
        reading = _reading([_pulse(60), _pulse(62)], [STEM_A, STEM_B], _heard(STEM_A, STEM_B))

        assert reading == [_pulse(60), _pulse(62)]

    def test_a_resting_frame_reads_through_whatever_is_heard(self) -> None:
        reading = _reading([_silence(), _pulse(62)], [RESTING_STEM_ID, STEM_B], _heard(STEM_B))

        assert reading == [_silence(), _pulse(62)]

    def test_a_frame_the_reader_wrote_reads_through_whatever_is_heard(self) -> None:
        reading = _reading([_pulse(60), _pulse(62)], [AUTHORED_STEM_ID, STEM_B], _heard())

        assert reading == [_pulse(60)]


class TestWhereTheReadingKeepsItsFrames:
    """The reading states a frame at the index it stands on, so it lines up with the record."""

    def test_a_run_of_frames_left_out_keeps_every_place(self) -> None:
        reading = _reading(
            [_pulse(60), _pulse(62), _pulse(64), _pulse(66)],
            [STEM_A, STEM_B, STEM_B, STEM_A],
            _heard(STEM_A),
        )

        assert reading == [_pulse(60), _silence(), _silence(), _pulse(66)]

    def test_a_leading_rest_keeps_its_place(self) -> None:
        reading = _reading(
            [_silence(), _pulse(62)],
            [RESTING_STEM_ID, STEM_A],
            _heard(STEM_A),
        )

        assert reading == [_silence(), _pulse(62)]

    def test_the_whole_selection_reads_the_stream_itself(self) -> None:
        stream = [_pulse(60), _silence(), _pulse(64)]

        reading = _reading(stream, [STEM_A, RESTING_STEM_ID, STEM_B], _heard(STEM_A, STEM_B))

        assert reading == stream


class TestWhereTheReadingEnds:
    """The reading runs to its last sounding frame, so what is heard states what it costs."""

    def test_a_trailing_frame_left_out_leaves_the_reading(self) -> None:
        reading = _reading(
            [_pulse(60), _pulse(62), _pulse(64)],
            [STEM_A, STEM_B, STEM_B],
            _heard(STEM_A),
        )

        assert reading == [_pulse(60)]

    def test_a_trailing_rest_leaves_the_reading(self) -> None:
        reading = _reading(
            [_pulse(60), _silence()],
            [STEM_A, RESTING_STEM_ID],
            _heard(STEM_A),
        )

        assert reading == [_pulse(60)]

    def test_a_channel_with_nothing_heard_reads_as_standing_by(self) -> None:
        reading = _reading([_pulse(60), _pulse(62)], [STEM_A, STEM_B], _heard())

        assert reading == []

    def test_a_channel_standing_by_reads_as_it_stands(self) -> None:
        instructions: Dict[ChannelName, Sequence[InstructionUnion]] = {CHANNEL: []}

        reading = heard_instructions(_stems_data([]), instructions, _heard(STEM_A))

        assert reading[CHANNEL] == []
