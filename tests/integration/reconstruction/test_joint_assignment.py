from pathlib import Path
from typing import Any, Dict, Final, FrozenSet, List, Mapping

import numpy as np
import pytest

from sampletones_core.audio import write_wave
from sampletones_core.configs import Config
from sampletones_core.configs.generation import ChannelInertia
from sampletones_core.constants.enums import AssignmentMethod, ChannelName
from sampletones_core.fft import Window
from sampletones_core.fft.features import get_feature_extractor
from sampletones_core.generators import get_generators_by_channels
from sampletones_core.generators.render import render_instructions
from sampletones_core.instructions import InstructionUnion, NoiseInstruction, PulseInstruction, TriangleInstruction
from sampletones_core.library import InstructionLibrary, InstructionLibraryData, InstructionLibraryFragment
from sampletones_core.reconstructions import Reconstruction, Reconstructor
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings

EVERY_CHANNEL: Final[List[ChannelName]] = ChannelName.items()
PULSE_PITCHES: Final[FrozenSet[int]] = frozenset({48, 55, 60, 64, 67, 72})
PULSE_VOLUMES: Final[FrozenSet[int]] = frozenset({4, 8, 12, 15})
DUTY_CYCLES: Final[FrozenSet[int]] = frozenset({1, 2})
TRIANGLE_PITCHES: Final[FrozenSet[int]] = frozenset({48, 55, 60, 64})
NOISE_PERIODS: Final[FrozenSet[int]] = frozenset({4, 8})
FRAMES: Final[int] = 24
EDGE_FRAMES: Final[int] = 3
RIGHT_SHARE: Final[float] = 0.9
LEAD: Final[PulseInstruction] = PulseInstruction(on=True, pitch=64, volume=12, duty_cycle=2)
CHORD: Final[Dict[ChannelName, InstructionUnion]] = {
    ChannelName.PULSE1: LEAD,
    ChannelName.PULSE2: PulseInstruction(on=True, pitch=67, volume=8, duty_cycle=1),
    ChannelName.TRIANGLE: TriangleInstruction(on=True, pitch=48),
}
HELD: Final[range] = range(EDGE_FRAMES, FRAMES - EDGE_FRAMES)
NEIGHBOR_PASSES: Final[int] = 1
TONAL_INERTIA: Final[float] = 0.5


def _kept(instruction: InstructionUnion) -> bool:
    if not instruction.on:
        return True

    match instruction:
        case PulseInstruction():
            return (
                instruction.pitch in PULSE_PITCHES
                and instruction.volume in PULSE_VOLUMES
                and instruction.duty_cycle in DUTY_CYCLES
            )
        case TriangleInstruction():
            return instruction.pitch in TRIANGLE_PITCHES
        case NoiseInstruction():
            return instruction.period in NOISE_PERIODS and instruction.volume in PULSE_VOLUMES and not instruction.short
        case _:
            return False


def _library(config: Config) -> InstructionLibrary:
    """A few notes of every kind around the chord, at a spread of volumes."""
    window = Window.from_config(config)
    extractor = get_feature_extractor(config, window)
    data: Dict[InstructionUnion, InstructionLibraryFragment[Any]] = {}
    for generator in get_generators_by_channels(
        config, [ChannelName.PULSE1, ChannelName.TRIANGLE, ChannelName.NOISE]
    ).values():
        for instruction in generator.get_possible_instructions():
            if _kept(instruction):
                data[instruction] = InstructionLibraryFragment.create(generator, instruction, extractor)

    library = InstructionLibrary()
    library.data[library.create_key(config, window)] = InstructionLibraryData.create(config, data)
    return library


def _rendered(path: Path, config: Config, played: Mapping[ChannelName, InstructionUnion]) -> Path:
    audio = sum(
        render_instructions([instruction] * FRAMES, channel_name, config)
        for channel_name, instruction in played.items()
    )
    write_wave(path, config.library.sample_rate, np.asarray(audio, dtype=np.float32))
    return path


def _joint_config() -> Config:
    config = Config()
    return config.model_copy(
        update={
            "generation": config.generation.model_copy(
                update={
                    "assignment": config.generation.assignment.model_copy(update={"method": AssignmentMethod.JOINT})
                }
            )
        }
    )


def _kept_config() -> Config:
    """The joint assignment with one neighbor pass, its tonal channels kept to their neighbors."""
    config = _joint_config()
    assignment = config.generation.assignment.model_copy(
        update={
            "neighbors": NEIGHBOR_PASSES,
            "inertia": ChannelInertia(pulse1=TONAL_INERTIA, pulse2=TONAL_INERTIA, triangle=TONAL_INERTIA, noise=0.0),
        }
    )
    return config.model_copy(update={"generation": config.generation.model_copy(update={"assignment": assignment})})


def _converted(
    directory: Path,
    library: InstructionLibrary,
    played: Mapping[ChannelName, InstructionUnion],
    settings: StemSettings,
    config: Config,
) -> Reconstruction:
    """``played`` held for every frame, converted under ``config`` with one stem of ``settings``."""
    path = _rendered(directory / "played.wav", config, played)
    reconstructor = Reconstructor(config, frozenset(EVERY_CHANNEL), library=library)
    reconstruction = reconstructor.reconstruct([path], StemsConfig.single_entry(settings))
    assert reconstruction is not None
    return reconstruction


def _sounding(reconstruction: Reconstruction, frame: int) -> Dict[ChannelName, InstructionUnion]:
    """What each channel sounding in ``frame`` plays; a channel standing by holds no frame and sounds none."""
    sounding: Dict[ChannelName, InstructionUnion] = {}
    for channel, stream in reconstruction.instructions.items():
        if stream and stream[frame].on:
            sounding[channel] = stream[frame]

    return sounding


@pytest.fixture(name="library", scope="module")
def library_fixture() -> InstructionLibrary:
    return _library(_joint_config())


@pytest.fixture(name="reconstruction", scope="module")
def reconstruction_fixture(tmp_path_factory: pytest.TempPathFactory, library: InstructionLibrary) -> Reconstruction:
    return _converted(
        tmp_path_factory.mktemp("chord"),
        library,
        CHORD,
        StemSettings(channels=EVERY_CHANNEL, bends=[]),
        _joint_config(),
    )


def _right_frames(reconstruction: Reconstruction) -> int:
    """How many held frames play the chord's notes, each on its own kind of channel."""
    instructions = reconstruction.instructions
    right = 0
    for frame in HELD:
        pulses = {
            instructions[channel][frame].pitch
            for channel in (ChannelName.PULSE1, ChannelName.PULSE2)
            if isinstance(instructions[channel][frame], PulseInstruction) and instructions[channel][frame].on
        }
        triangle = instructions[ChannelName.TRIANGLE][frame]
        right += (
            pulses == {64, 67} and triangle.on and isinstance(triangle, TriangleInstruction) and triangle.pitch == 48
        )

    return right


class TestAJointConversionOfAChord:
    def test_the_chord_s_notes_play_on_their_own_kinds_of_channel(self, reconstruction: Reconstruction) -> None:
        assert _right_frames(reconstruction) >= RIGHT_SHARE * len(HELD)


class TestAJointConversionOfAChordBesideItsNeighbors:
    """A held chord assigned again among its neighbors, kept to them, keeps its notes."""

    def test_the_chord_s_notes_play_on_their_own_kinds_of_channel(
        self, tmp_path_factory: pytest.TempPathFactory, library: InstructionLibrary
    ) -> None:
        reconstruction = _converted(
            tmp_path_factory.mktemp("kept"),
            library,
            CHORD,
            StemSettings(channels=EVERY_CHANNEL, bends=[]),
            _kept_config(),
        )

        assert _right_frames(reconstruction) >= RIGHT_SHARE * len(HELD)


class TestAJointConversionOfAStemCountedToOneChannel:
    """Every combination the search reaches keeps within the stem's count, so the conversion does too."""

    def test_no_frame_sounds_more_than_one_channel(
        self, tmp_path_factory: pytest.TempPathFactory, library: InstructionLibrary
    ) -> None:
        reconstruction = _converted(
            tmp_path_factory.mktemp("counted"),
            library,
            CHORD,
            StemSettings(channels=EVERY_CHANNEL, bends=[], channel_cap=1),
            _joint_config(),
        )

        assert all(len(_sounding(reconstruction, frame)) <= 1 for frame in range(FRAMES))


class TestAJointConversionOfALoneNote:
    """A lone note is fitted whole on one channel, and the notes covering its partials are left out."""

    def test_the_note_plays_on_one_pulse_alone(
        self, tmp_path_factory: pytest.TempPathFactory, library: InstructionLibrary
    ) -> None:
        reconstruction = _converted(
            tmp_path_factory.mktemp("lone"),
            library,
            {ChannelName.PULSE1: LEAD},
            StemSettings(channels=EVERY_CHANNEL, bends=[]),
            _joint_config(),
        )

        right = 0
        for frame in HELD:
            sounding = list(_sounding(reconstruction, frame).values())
            right += (
                len(sounding) == 1 and isinstance(sounding[0], PulseInstruction) and sounding[0].pitch == LEAD.pitch
            )

        assert right >= RIGHT_SHARE * len(HELD)
