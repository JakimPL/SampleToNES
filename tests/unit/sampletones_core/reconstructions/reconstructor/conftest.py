from typing import Any, Dict, Final, FrozenSet, List, Mapping

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.algorithm import STEM_ACTIVITY_FLOOR
from sampletones_core.constants.enums import (
    DEFAULT_CHANNELS,
    ChannelName,
    GeneratorClassName,
)
from sampletones_core.fft import Fragment, Window
from sampletones_core.fft.features import FeatureExtractor, get_feature_extractor
from sampletones_core.fft.fragment.audio import FragmentedAudio
from sampletones_core.generators import GeneratorUnion, get_generators_by_channels
from sampletones_core.generators.render import render_instructions
from sampletones_core.instructions import InstructionUnion, NoiseInstruction, PulseInstruction, TriangleInstruction
from sampletones_core.library import InstructionLibraryData, InstructionLibraryFragment
from sampletones_core.reconstructions.reconstructor.matching import FrameMatcher
from sampletones_core.reconstructions.reconstructor.worker import ReconstructorWorker

INSTRUCTIONS_PER_GENERATOR_IN_TEST_LIBRARY: Final[int] = 3
WORKER_SIGNAL_LENGTH: Final[int] = 1 << 20
RENDERED_FRAMES: Final[int] = 5
JOINT_PULSE_PITCHES: Final[FrozenSet[int]] = frozenset({48, 57, 60, 64, 67})
JOINT_PULSE_VOLUMES: Final[FrozenSet[int]] = frozenset({4, 8, 11, 12, 15})
JOINT_DUTY_CYCLES: Final[FrozenSet[int]] = frozenset({1, 2})
JOINT_TRIANGLE_PITCHES: Final[FrozenSet[int]] = frozenset({45, 48, 57, 60})
JOINT_NOISE_PERIODS: Final[FrozenSet[int]] = frozenset({4, 8})
JOINT_NOISE_VOLUMES: Final[FrozenSet[int]] = frozenset({8, 15})
JOINT_SIGNAL_LENGTH: Final[int] = 1 << 20


@pytest.fixture(scope="module")
def config() -> Config:
    return Config()


@pytest.fixture(scope="module")
def window(config: Config) -> Window:
    return Window.from_config(config)


@pytest.fixture(scope="module")
def extractor(config: Config, window: Window) -> FeatureExtractor:
    return get_feature_extractor(config, window)


@pytest.fixture(scope="module")
def channels(config: Config) -> Dict[ChannelName, GeneratorUnion]:
    return get_generators_by_channels(config, DEFAULT_CHANNELS)


@pytest.fixture(scope="module")
def library_data(
    config: Config,
    extractor: FeatureExtractor,
    channels: Dict[ChannelName, GeneratorUnion],
) -> InstructionLibraryData:
    data: Dict[InstructionUnion, InstructionLibraryFragment[Any]] = {}
    for generator in channels.values():
        for instruction in list(generator.get_possible_instructions())[:INSTRUCTIONS_PER_GENERATOR_IN_TEST_LIBRARY]:
            data[instruction] = InstructionLibraryFragment.create(generator, instruction, extractor)

    return InstructionLibraryData.create(config, data)


@pytest.fixture(scope="module")
def worker(
    config: Config,
    window: Window,
    channels: Dict[ChannelName, GeneratorUnion],
    library_data: InstructionLibraryData,
) -> ReconstructorWorker:
    return ReconstructorWorker(
        config=config,
        window=window,
        channels=channels,
        library_data=library_data,
        signal_length=WORKER_SIGNAL_LENGTH,
    )


@pytest.fixture(scope="module")
def audible_instruction(library_data: InstructionLibraryData) -> InstructionUnion:
    return next(
        instruction
        for instruction in library_data.keys()
        if instruction.on and bool(np.any(library_data[instruction].sample.array))
    )


@pytest.fixture
def synthetic_fragment(
    library_data: InstructionLibraryData,
    config: Config,
    window: Window,
) -> Fragment:
    """A frame of sound a channel renders, the stand-in for what one stem contributes."""
    return _renderable_fragments(library_data, config, window)[0]


@pytest.fixture
def audible_fragments(
    library_data: InstructionLibraryData,
    config: Config,
    window: Window,
) -> List[Fragment]:
    """The distinct sounds a case hands its stems, each loud enough for a channel to render."""
    return _renderable_fragments(library_data, config, window)


def _renderable_fragments(
    library_data: InstructionLibraryData,
    config: Config,
    window: Window,
) -> List[Fragment]:
    """The library's frames loud enough to render, which is what the assignment asks of a stem."""
    fragments = [
        library_data[instruction].get_fragment(0, config, window)
        for instruction in library_data.keys()
        if instruction.on
    ]
    return [fragment for fragment in fragments if float(np.max(np.abs(fragment.audio))) > STEM_ACTIVITY_FLOOR]


@pytest.fixture
def fragmented_audio(
    config: Config,
    window: Window,
    synthetic_fragment: Fragment,
) -> FragmentedAudio:
    audio = np.tile(synthetic_fragment.audio, 3).astype(np.float32)
    return FragmentedAudio.create(audio, config, window)


@pytest.fixture(scope="module")
def all_channels(config: Config) -> Dict[ChannelName, GeneratorUnion]:
    return get_generators_by_channels(config, ChannelName.items())


def rendered_audio(config: Config, instructions: Mapping[ChannelName, InstructionUnion], frames: int) -> np.ndarray:
    """The channels playing ``instructions`` together, each note held for ``frames`` frames."""
    return sum(
        (
            render_instructions([instruction] * frames, channel_name, config)
            for channel_name, instruction in instructions.items()
        ),
        start=np.zeros(frames * config.library.frame_length, dtype=np.float32),
    )


def rendered_fragment(
    config: Config,
    extractor: FeatureExtractor,
    instructions: Mapping[ChannelName, InstructionUnion],
) -> Fragment:
    """A frame of the channels playing ``instructions`` together, taken from the middle of a held note."""
    return extractor.extract(rendered_audio(config, instructions, RENDERED_FRAMES))[RENDERED_FRAMES // 2]


def _in_joint_library(instruction: InstructionUnion) -> bool:
    """Whether the joint search's test library holds ``instruction``: a few notes at a spread of volumes."""
    if not instruction.on:
        return True

    match instruction:
        case PulseInstruction():
            return (
                instruction.pitch in JOINT_PULSE_PITCHES
                and instruction.volume in JOINT_PULSE_VOLUMES
                and instruction.duty_cycle in JOINT_DUTY_CYCLES
            )
        case TriangleInstruction():
            return instruction.pitch in JOINT_TRIANGLE_PITCHES
        case NoiseInstruction():
            return (
                instruction.period in JOINT_NOISE_PERIODS
                and instruction.volume in JOINT_NOISE_VOLUMES
                and not instruction.short
            )
        case _:
            return False


@pytest.fixture(scope="module")
def joint_library(
    config: Config,
    extractor: FeatureExtractor,
    all_channels: Dict[ChannelName, GeneratorUnion],
) -> InstructionLibraryData:
    """A few pulse, triangle and noise notes at several volumes, which chords of those notes are drawn from."""
    data: Dict[InstructionUnion, InstructionLibraryFragment[Any]] = {}
    generators: Dict[GeneratorClassName, GeneratorUnion] = {}
    for generator in all_channels.values():
        generators.setdefault(generator.class_name(), generator)
    for generator in generators.values():
        for instruction in generator.get_possible_instructions():
            if _in_joint_library(instruction):
                data[instruction] = InstructionLibraryFragment.create(generator, instruction, extractor)

    return InstructionLibraryData.create(config, data)


@pytest.fixture(scope="module")
def joint_matcher(
    config: Config,
    window: Window,
    all_channels: Dict[ChannelName, GeneratorUnion],
    joint_library: InstructionLibraryData,
) -> FrameMatcher:
    """The matcher of the joint search's test library, over every channel."""
    return ReconstructorWorker(
        config=config,
        window=window,
        channels=all_channels,
        library_data=joint_library,
        signal_length=JOINT_SIGNAL_LENGTH,
    ).matcher
