from pathlib import Path
from typing import Dict, List

import numpy as np
import pytest

from sampletones_core.audio.mixing import mix
from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters.naming import instrument_slice_name
from sampletones_core.exports.request import InstrumentExport, SampleExport
from sampletones_core.generators.render import render_channels
from sampletones_core.instructions import InstructionUnion
from sampletones_core.project.instruments.sample import Sample
from sampletones_core.timers.utils import get_timer_table
from sampletones_player.builder import instructions_from_instruments, song_from_sample
from sampletones_player.export import NSFBackend
from sampletones_player.specification.nsf import NSF_MAGIC
from sampletones_shared.paths.extensions import EXT_FILE_NSF
from tests.integration.nsf.console.instructions import instructions_from_trace
from tests.integration.nsf.console.session import captured_file_trace

ChannelInstructions = Dict[ChannelName, List[InstructionUnion]]


def resting(instruction: InstructionUnion) -> InstructionUnion:
    """A sounding instruction as it stands, and a rest as the canonical silent one.

    A stream holds a channel's pitch and timbre through a rest so the driver leaves the timer's
    high byte alone, so what a rest carries beyond its silence is the channel's own history.
    """
    if instruction.on:
        return instruction

    silent: InstructionUnion = type(instruction).null_instruction()
    return silent


def sample_request(sample: Sample) -> SampleExport:
    """The request the application hands a backend for one loaded reconstruction.

    A reconstruction reaches an export as the envelopes each of its playing channels carries,
    which is the same reading the instruments panel and every tracker format are given.
    """
    config = sample.reconstruction.config
    features_by_channel = sample.reconstruction.export()

    return SampleExport(
        name=sample.name,
        instruments=tuple(
            InstrumentExport(
                name=instrument_slice_name(sample.name, channel),
                channel=channel,
                features=features,
                loop=sample.loop,
                nes_frequency=config.nes_frequency,
                tuning=config.tuning,
            )
            for channel, features in features_by_channel.items()
            if features.has_frames
        ),
        nes_frequency=config.nes_frequency,
        tuning=config.tuning,
    )


@pytest.fixture(scope="module")
def backend() -> NSFBackend:
    return NSFBackend()


@pytest.fixture(scope="module")
def requests(instrument_catalog: Dict[str, Sample]) -> Dict[str, SampleExport]:
    """The export request each catalog sample reaches a backend as."""
    return {name: sample_request(sample) for name, sample in instrument_catalog.items()}


@pytest.fixture(scope="module")
def exported(
    backend: NSFBackend,
    requests: Dict[str, SampleExport],
    tmp_path_factory: pytest.TempPathFactory,
) -> Dict[str, Path]:
    """Every catalog sample written to disk through the backend the application registers."""
    directory = tmp_path_factory.mktemp("nsf-backend")
    paths: Dict[str, Path] = {}
    for name, request in requests.items():
        destination = directory / f"{name}{EXT_FILE_NSF}"
        backend.write_sample(destination, request)
        paths[name] = destination

    return paths


@pytest.fixture(scope="module")
def played(
    exported: Dict[str, Path],
    requests: Dict[str, SampleExport],
    instrument_catalog: Dict[str, Sample],
) -> Dict[str, ChannelInstructions]:
    """What the console sounds when it plays each written file, read back out of its register writes."""
    played: Dict[str, ChannelInstructions] = {}
    for name, destination in exported.items():
        song = song_from_sample(requests[name])
        trace = captured_file_trace(destination.read_bytes(), song)
        played[name] = instructions_from_trace(
            trace,
            get_timer_table(instrument_catalog[name].reconstruction.config.tuning),
        )

    return played


class TestTheBackendWritesAPlayableProgram:
    """What reaches disk when the application exports a reconstruction to the console."""

    def test_every_sample_reaches_a_file_a_player_recognizes(self, exported: Dict[str, Path]) -> None:
        for destination in exported.values():
            assert destination.read_bytes()[: len(NSF_MAGIC)] == NSF_MAGIC

    def test_the_catalog_sounds_all_four_channels(self, played: Dict[str, ChannelInstructions]) -> None:
        sounded = {
            channel
            for instructions in played.values()
            for channel, stream in instructions.items()
            if any(instruction.on for instruction in stream)
        }
        assert sounded == set(ChannelName.items())


class TestTheConsoleSoundsTheRequest:
    """The envelopes an export request carries, read back off the APU the file drives."""

    def test_every_slice_sounds_the_instructions_its_envelopes_describe(
        self,
        played: Dict[str, ChannelInstructions],
        requests: Dict[str, SampleExport],
    ) -> None:
        for name, request in requests.items():
            for channel, instructions in instructions_from_instruments(request.instruments).items():
                sounded = played[name][channel][: len(instructions)]
                assert [resting(instruction) for instruction in sounded] == [
                    resting(instruction) for instruction in instructions
                ]

    def test_a_channel_the_request_leaves_out_rests_throughout(
        self,
        played: Dict[str, ChannelInstructions],
        requests: Dict[str, SampleExport],
    ) -> None:
        for name, request in requests.items():
            carried = {instrument.channel for instrument in request.instruments}
            for channel in set(ChannelName.items()) - carried:
                assert not any(instruction.on for instruction in played[name][channel])

    def test_the_console_sounds_the_reconstructions_own_waveform(
        self,
        played: Dict[str, ChannelInstructions],
        instrument_catalog: Dict[str, Sample],
    ) -> None:
        """The envelopes state the span a reconstruction is audible over, so the console sounds the
        very waveform it was built as there, and what lies past that span is silence on both sides.
        """
        for name, sample in instrument_catalog.items():
            rendered = mix(list(render_channels(played[name], sample.reconstruction.config).values()))
            approximation = sample.reconstruction.approximation
            audible = min(len(rendered), len(approximation))

            assert np.array_equal(rendered[:audible], approximation[:audible])
            assert not np.any(rendered[audible:])
            assert not np.any(approximation[audible:])
