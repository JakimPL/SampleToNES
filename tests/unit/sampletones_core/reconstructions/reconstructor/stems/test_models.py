from typing import Final, Tuple

import numpy as np

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, HierarchyMode
from sampletones_core.fft import Fragment
from sampletones_core.instructions import PulseInstruction, TriangleInstruction
from sampletones_core.reconstructions.reconstructor.stems.models.choice import StemChoice
from sampletones_core.reconstructions.reconstructor.stems.models.frame_assignment import StemFrameAssignment
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
        StemChoice(
            stem_id=0,
            channel_name=ChannelName.PULSE1,
            instruction=PulseInstruction.default_instruction(),
            approximation=fragment,
            cost=FRAME_COST,
        ),
        StemChoice(
            stem_id=1,
            channel_name=ChannelName.TRIANGLE,
            instruction=TriangleInstruction.default_instruction(),
            approximation=fragment,
            cost=FRAME_COST,
        ),
    )


class TestStemFrameAssignment:
    def test_by_channel_names_the_stem_holding_each_channel(self) -> None:
        first, second = _choices(Config())

        assignment = StemFrameAssignment(choices=(first, second), resting=())

        assert assignment.by_channel == {
            ChannelName.PULSE1: first,
            ChannelName.TRIANGLE: second,
        }

    def test_picked_and_resting_channels_stay_apart(self) -> None:
        first, _ = _choices(Config())

        assignment = StemFrameAssignment(choices=(first,), resting=(ChannelName.NOISE,))

        assert set(assignment.by_channel).isdisjoint(assignment.resting)


class TestHierarchyMode:
    def test_values(self) -> None:
        assert tuple(HierarchyMode) == (HierarchyMode.ROUND_ROBIN, HierarchyMode.STRICT)
