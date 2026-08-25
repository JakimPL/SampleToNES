from typing import Any, Dict, Final, List

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.algorithm import STEM_ACTIVITY_FLOOR
from sampletones_core.constants.enums import ChannelName
from sampletones_core.fft import Fragment, Window
from sampletones_core.fft.features import FeatureExtractor, get_feature_extractor
from sampletones_core.fft.fragment.audio import FragmentedAudio
from sampletones_core.generators import GeneratorUnion, get_generators_by_channels
from sampletones_core.instructions import InstructionUnion
from sampletones_core.library import InstructionLibraryData, InstructionLibraryFragment
from sampletones_core.reconstructions.reconstructor.worker import ReconstructorWorker

INSTRUCTIONS_PER_GENERATOR_IN_TEST_LIBRARY: Final[int] = 3
WORKER_SIGNAL_LENGTH: Final[int] = 1 << 20


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
    return get_generators_by_channels(config, config.generation.channels)


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
