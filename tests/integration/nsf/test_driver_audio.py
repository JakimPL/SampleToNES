from typing import Dict, List

import numpy as np
import pytest

from sampletones_core.audio.mixing import mix
from sampletones_core.constants.enums import ChannelName
from sampletones_core.generators.render import render_channels
from sampletones_core.instructions import InstructionUnion
from sampletones_core.project.instruments.sample import Sample
from sampletones_core.timers.utils import get_timer_table
from sampletones_player.builder import song_from_reconstruction
from tests.integration.nsf.console.instructions import instructions_from_trace
from tests.integration.nsf.console.session import captured_trace
from tests.integration.nsf.exports import exported_information

ChannelInstructions = Dict[ChannelName, List[InstructionUnion]]


def played_by_console(sample: Sample) -> ChannelInstructions:
    """The per-tick instructions the console sounds, read back out of the registers it wrote."""
    song = song_from_reconstruction(sample.reconstruction, loop_tick=None)
    trace = captured_trace(song, exported_information(sample.name))
    return instructions_from_trace(trace, get_timer_table(sample.reconstruction.config))


def resting(instruction: InstructionUnion) -> InstructionUnion:
    """A sounding instruction as it stands, and a rest as the canonical silent one.

    A stream holds a channel's pitch and timbre through a rest so the driver leaves the timer's
    high byte alone, so what a rest carries beyond its silence is the channel's own history.
    """
    if instruction.on:
        return instruction

    silent: InstructionUnion = type(instruction).null_instruction()
    return silent


@pytest.fixture(scope="module")
def played(instrument_catalog: Dict[str, Sample]) -> Dict[str, ChannelInstructions]:
    """What the console sounds for every sample in the catalog, together covering all four channels."""
    return {name: played_by_console(sample) for name, sample in instrument_catalog.items()}


@pytest.fixture(scope="module")
def rendered(
    played: Dict[str, ChannelInstructions],
    instrument_catalog: Dict[str, Sample],
) -> Dict[str, np.ndarray]:
    """The waveform the console's instructions sound as, rendered on the reconstruction's own engine."""
    return {
        name: mix(list(render_channels(played[name], sample.reconstruction.config).values()))
        for name, sample in instrument_catalog.items()
    }


class TestTheConsoleSoundsTheReconstruction:
    """What the driver puts on the APU, decoded back into the terms the reconstruction speaks."""

    def test_every_played_channel_sounds_its_own_instructions(
        self,
        played: Dict[str, ChannelInstructions],
        instrument_catalog: Dict[str, Sample],
    ) -> None:
        for name, sample in instrument_catalog.items():
            for channel, instructions in sample.reconstruction.instructions.items():
                sounded = played[name][channel][: len(instructions)]
                assert [resting(instruction) for instruction in sounded] == [
                    resting(instruction) for instruction in instructions
                ]

    def test_a_channel_the_reconstruction_leaves_out_rests_throughout(
        self,
        played: Dict[str, ChannelInstructions],
        instrument_catalog: Dict[str, Sample],
    ) -> None:
        for name, sample in instrument_catalog.items():
            silent = set(ChannelName.items()) - set(sample.reconstruction.instructions)
            for channel in silent:
                assert not any(instruction.on for instruction in played[name][channel])

    def test_the_catalog_sounds_all_four_channels(self, played: Dict[str, ChannelInstructions]) -> None:
        sounded = {
            channel
            for instructions in played.values()
            for channel, stream in instructions.items()
            if any(instruction.on for instruction in stream)
        }
        assert sounded == set(ChannelName.items())

    def test_every_run_ends_with_every_channel_silent(self, played: Dict[str, ChannelInstructions]) -> None:
        for instructions in played.values():
            assert not any(stream[-1].on for stream in instructions.values())


class TestTheConsoleRendersTheReconstructionsAudio:
    """The captured trace, sounded through the very generators the reconstruction was built on."""

    def test_the_console_reproduces_the_reconstructions_waveform(
        self,
        rendered: Dict[str, np.ndarray],
        instrument_catalog: Dict[str, Sample],
    ) -> None:
        for name, sample in instrument_catalog.items():
            approximation = sample.reconstruction.approximation
            assert np.array_equal(rendered[name][: len(approximation)], approximation)

    def test_the_audio_past_the_reconstruction_is_silent(
        self,
        rendered: Dict[str, np.ndarray],
        instrument_catalog: Dict[str, Sample],
    ) -> None:
        for name, sample in instrument_catalog.items():
            approximation = sample.reconstruction.approximation
            assert not np.any(rendered[name][len(approximation) :])
