from dataclasses import dataclass
from typing import Final, Tuple

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_VOLUME
from sampletones_core.generators import CHANNEL_CLASSES, FULL_SCALE_RMS_LEVELS
from sampletones_core.generators.render import render_instructions
from sampletones_core.instructions import InstructionUnion, NoiseInstruction, PulseInstruction, TriangleInstruction
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

RENDERED_FRAMES: Final[int] = 120
LEVEL_TOLERANCE: Final[float] = 1e-2


class TestFullScaleRmsLevels(BaseTestSuite):
    """A channel at full volume renders the RMS level the working level is anchored to."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        channel_name: ChannelName
        instructions: Tuple[InstructionUnion, ...]

    test_cases = (
        TestCase(
            label="pulse_at_every_duty_cycle",
            channel_name=ChannelName.PULSE1,
            instructions=tuple(
                PulseInstruction(on=True, pitch=60, volume=MAX_VOLUME, duty_cycle=duty_cycle) for duty_cycle in range(4)
            ),
        ),
        TestCase(
            label="triangle_across_the_range",
            channel_name=ChannelName.TRIANGLE,
            instructions=tuple(TriangleInstruction(on=True, pitch=pitch) for pitch in (33, 57, 81)),
        ),
        TestCase(
            label="noise_at_long_periods",
            channel_name=ChannelName.NOISE,
            instructions=tuple(
                NoiseInstruction(on=True, period=period, volume=MAX_VOLUME, short=False) for period in (0, 3, 6)
            ),
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_a_full_volume_rendering_holds_the_level(self, test_case: TestCase) -> None:
        config = Config()
        generator_class_name = CHANNEL_CLASSES[test_case.channel_name].class_name()

        for instruction in test_case.instructions:
            audio = render_instructions([instruction] * RENDERED_FRAMES, test_case.channel_name, config)
            level = float(np.sqrt(np.mean(np.square(audio.astype(np.float64)))))

            assert level == pytest.approx(FULL_SCALE_RMS_LEVELS[generator_class_name], rel=LEVEL_TOLERANCE)
