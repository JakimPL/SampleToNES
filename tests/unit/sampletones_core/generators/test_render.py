from typing import Dict, List

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.generators.render import render_generators, render_instructions
from sampletones_core.instructions import (
    InstructionUnion,
    NoiseInstruction,
    PulseInstruction,
    TriangleInstruction,
)


@pytest.fixture
def config() -> Config:
    return Config()


@pytest.fixture
def pulse_stream() -> List[InstructionUnion]:
    return [
        PulseInstruction(on=True, pitch=60, volume=15, duty_cycle=0),
        PulseInstruction(on=True, pitch=60, volume=15, duty_cycle=0),
        PulseInstruction(on=False, pitch=60, volume=0, duty_cycle=0),
    ]


class TestRenderInstructions:
    """One channel's audio, rendered frame by frame from the instructions that drive it."""

    def test_every_instruction_renders_one_frame(
        self,
        pulse_stream: List[InstructionUnion],
        config: Config,
    ) -> None:
        rendered = render_instructions(pulse_stream, GeneratorName.PULSE1, config)
        assert len(rendered) == len(pulse_stream) * config.library.frame_length

    def test_a_held_note_runs_its_oscillator_on(
        self,
        pulse_stream: List[InstructionUnion],
        config: Config,
    ) -> None:
        frame_length = config.library.frame_length
        rendered = render_instructions(pulse_stream, GeneratorName.PULSE1, config)
        first = rendered[:frame_length]
        second = rendered[frame_length : 2 * frame_length]
        assert not np.array_equal(first, second)

    def test_a_rest_renders_silence(self, pulse_stream: List[InstructionUnion], config: Config) -> None:
        frame_length = config.library.frame_length
        rendered = render_instructions(pulse_stream, GeneratorName.PULSE1, config)
        assert not np.any(rendered[2 * frame_length :])

    def test_a_channel_describing_no_frame_raises(self, config: Config) -> None:
        with pytest.raises(ValueError):
            render_instructions([], GeneratorName.PULSE1, config)


class TestRenderGenerators:
    """The audio of every channel that describes a frame, in channel order."""

    @pytest.fixture
    def streams(self, pulse_stream: List[InstructionUnion]) -> Dict[GeneratorName, List[InstructionUnion]]:
        return {
            GeneratorName.PULSE1: pulse_stream,
            GeneratorName.TRIANGLE: [TriangleInstruction(on=True, pitch=48)],
            GeneratorName.NOISE: [NoiseInstruction(on=True, period=4, volume=15, short=False)],
        }

    def test_every_sounding_channel_renders(
        self,
        streams: Dict[GeneratorName, List[InstructionUnion]],
        config: Config,
    ) -> None:
        assert set(render_generators(streams, config)) == set(streams)

    def test_a_channel_standing_by_renders_nothing(
        self,
        streams: Dict[GeneratorName, List[InstructionUnion]],
        config: Config,
    ) -> None:
        streams[GeneratorName.PULSE2] = []
        assert GeneratorName.PULSE2 not in render_generators(streams, config)

    def test_the_channels_come_back_in_channel_order(
        self,
        streams: Dict[GeneratorName, List[InstructionUnion]],
        config: Config,
    ) -> None:
        rendered = render_generators(streams, config)
        assert list(rendered) == [name for name in GeneratorName.items() if name in streams]

    def test_a_channel_sounds_what_it_renders_on_its_own(
        self,
        streams: Dict[GeneratorName, List[InstructionUnion]],
        config: Config,
    ) -> None:
        rendered = render_generators(streams, config)
        for generator_name, instructions in streams.items():
            assert np.array_equal(
                rendered[generator_name],
                render_instructions(instructions, generator_name, config),
            )
