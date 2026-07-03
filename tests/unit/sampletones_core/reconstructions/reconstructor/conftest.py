from typing import Any, Dict, Final

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.fft import Fragment, Window
from sampletones_core.fft.features import FeatureExtractor, get_feature_extractor
from sampletones_core.fft.fragment.audio import FragmentedAudio
from sampletones_core.generators import GeneratorUnion, get_generators_by_names
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
def generators(config: Config) -> Dict[GeneratorName, GeneratorUnion]:
    return get_generators_by_names(config, config.generation.generators)


@pytest.fixture(scope="module")
def library_data(
    config: Config,
    extractor: FeatureExtractor,
    generators: Dict[GeneratorName, GeneratorUnion],
) -> InstructionLibraryData:
    data: Dict[InstructionUnion, InstructionLibraryFragment[Any]] = {}
    for generator in generators.values():
        for instruction in list(generator.get_possible_instructions())[:INSTRUCTIONS_PER_GENERATOR_IN_TEST_LIBRARY]:
            data[instruction] = InstructionLibraryFragment.create(generator, instruction, extractor)

    return InstructionLibraryData.create(config, data)


@pytest.fixture(scope="module")
def worker(
    config: Config,
    window: Window,
    generators: Dict[GeneratorName, GeneratorUnion],
    library_data: InstructionLibraryData,
) -> ReconstructorWorker:
    return ReconstructorWorker(
        config=config,
        window=window,
        generators=generators,
        library_data=library_data,
        signal_length=WORKER_SIGNAL_LENGTH,
    )


@pytest.fixture
def synthetic_fragment(
    library_data: InstructionLibraryData,
    config: Config,
    window: Window,
) -> Fragment:
    active_instruction = next(instrument for instrument in library_data.keys() if instrument.on)
    return library_data[active_instruction].get_fragment(0, config, window)


@pytest.fixture
def fragmented_audio(
    config: Config,
    window: Window,
    synthetic_fragment: Fragment,
) -> FragmentedAudio:
    audio = np.tile(synthetic_fragment.audio, 3).astype(np.float32)
    return FragmentedAudio.create(audio, config, window)
