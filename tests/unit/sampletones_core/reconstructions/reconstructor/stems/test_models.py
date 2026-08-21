from typing import Final, Tuple

import numpy as np

from sampletones_core.configs import Config
from sampletones_core.constants.algorithm import RESTING_FRAME_COST, RESTING_STEM_ID
from sampletones_core.constants.enums import ChannelName, HierarchyMode
from sampletones_core.fft import Fragment
from sampletones_core.instructions import (
    InstructionUnion,
    NoiseInstruction,
    PulseInstruction,
    TriangleInstruction,
)
from sampletones_core.reconstructions.reconstructor.matching import ScoredCandidate
from sampletones_core.reconstructions.reconstructor.stems.assignment.track import TrackAssignment
from sampletones_core.reconstructions.reconstructor.stems.models.choice import StemChoice
from sampletones_core.reconstructions.reconstructor.stems.models.frame_assignment import StemFrameAssignment
from sampletones_core.reconstructions.reconstructor.stems.models.rest import StemRest
from sampletones_core.structures.histogram import Histogram

FRAME_COST: Final[float] = 0.5


def _fragment(config: Config) -> Fragment:
    audio = np.zeros(config.frame_length, dtype=np.float32)
    return Fragment(
        audio=audio,
        feature=Histogram(edges=np.array([0.0, 1.0], dtype=np.float32), values=np.zeros(1, dtype=np.float32)),
        windowed_audio=audio,
        config=config,
    )


def _choices(config: Config) -> Tuple[StemChoice, StemChoice]:
    fragment = _fragment(config)
    return (
        _choice(0, ChannelName.PULSE1, PulseInstruction.default_instruction(), fragment),
        _choice(1, ChannelName.TRIANGLE, TriangleInstruction.default_instruction(), fragment),
    )


def _choice(
    stem_id: int,
    channel_name: ChannelName,
    instruction: InstructionUnion,
    fragment: Fragment,
) -> StemChoice:
    return StemChoice(
        stem_id=stem_id,
        channel_name=channel_name,
        instruction=instruction,
        approximation=fragment,
        cost=FRAME_COST,
        column=(ScoredCandidate(instruction=instruction, cost=FRAME_COST, approximation=fragment),),
    )


def _rest(config: Config) -> StemRest:
    fragment = _fragment(config)
    instruction = NoiseInstruction.null_instruction()
    return StemRest(
        channel_name=ChannelName.NOISE,
        column=(ScoredCandidate(instruction=instruction, cost=RESTING_FRAME_COST, approximation=fragment),),
    )


class TestStemFrameAssignment:
    def test_by_channel_names_the_stem_holding_each_channel(self) -> None:
        first, second = _choices(Config())

        assignment = StemFrameAssignment(choices=(first, second), rests=())

        assert assignment.by_channel == {
            ChannelName.PULSE1: first,
            ChannelName.TRIANGLE: second,
        }

    def test_picked_and_resting_channels_stay_apart(self) -> None:
        config = Config()
        first, _ = _choices(config)

        assignment = StemFrameAssignment(choices=(first,), rests=(_rest(config),))

        assert assignment.resting == (ChannelName.NOISE,)
        assert set(assignment.by_channel).isdisjoint(assignment.resting)


class TestTrackAssignment:
    def test_a_frame_reaches_every_channel_it_answers(self) -> None:
        config = Config()
        first, second = _choices(config)
        rest = _rest(config)

        track = TrackAssignment([ChannelName.PULSE1, ChannelName.TRIANGLE, ChannelName.NOISE])
        track.add(StemFrameAssignment(choices=(first, second), rests=(rest,)))

        assert track.stem_ids == {
            ChannelName.PULSE1: [first.stem_id],
            ChannelName.TRIANGLE: [second.stem_id],
            ChannelName.NOISE: [RESTING_STEM_ID],
        }
        assert track.lattices[ChannelName.PULSE1] == [first.column]
        assert track.lattices[ChannelName.NOISE] == [rest.column]

    def test_a_channel_resting_throughout_is_named_resting(self) -> None:
        config = Config()
        first, _ = _choices(config)
        rest = _rest(config)

        track = TrackAssignment([ChannelName.PULSE1, ChannelName.NOISE])
        for _ in range(3):
            track.add(StemFrameAssignment(choices=(first,), rests=(rest,)))

        assert track.resting_channels == [ChannelName.NOISE]

    def test_a_channel_that_sounds_once_keeps_its_place(self) -> None:
        config = Config()
        first, _ = _choices(config)
        rest = _rest(config)
        noise_choice = _choice(0, ChannelName.NOISE, NoiseInstruction.default_instruction(), _fragment(config))

        track = TrackAssignment([ChannelName.PULSE1, ChannelName.NOISE])
        track.add(StemFrameAssignment(choices=(first,), rests=(rest,)))
        track.add(StemFrameAssignment(choices=(first, noise_choice), rests=()))

        assert track.resting_channels == []
        assert track.stem_ids[ChannelName.NOISE] == [RESTING_STEM_ID, 0]

    def test_dropping_a_channel_releases_both_records(self) -> None:
        config = Config()
        first, _ = _choices(config)
        rest = _rest(config)

        track = TrackAssignment([ChannelName.PULSE1, ChannelName.NOISE])
        track.add(StemFrameAssignment(choices=(first,), rests=(rest,)))
        track.drop(ChannelName.NOISE)

        assert set(track.lattices) == {ChannelName.PULSE1}
        assert set(track.stem_ids) == {ChannelName.PULSE1}


class TestHierarchyMode:
    def test_values(self) -> None:
        assert tuple(HierarchyMode) == (HierarchyMode.ROUND_ROBIN, HierarchyMode.STRICT)
