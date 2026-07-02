from pathlib import Path
from typing import Any, Dict, Final, FrozenSet, List

import numpy as np

from sampletones_core.audio import write_wave
from sampletones_core.configs import Config
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.fft import Window
from sampletones_core.fft.features import get_feature_extractor
from sampletones_core.generators import get_generators_by_names
from sampletones_core.instructions import InstructionUnion
from sampletones_core.library import (
    InstructionLibrary,
    InstructionLibraryData,
    InstructionLibraryFragment,
)
from sampletones_core.project.instruments.sample import Sample
from sampletones_core.reconstructions import Reconstruction, Reconstructor
from sampletones_shared.types.path import Pathlike

INSTRUCTIONS_PER_GENERATOR: Final[int] = 8
LIBRARY_GENERATORS: Final[List[GeneratorName]] = [
    GeneratorName.PULSE1,
    GeneratorName.TRIANGLE,
    GeneratorName.NOISE,
]


def build_mini_library(config: Config, *, per_generator: int = INSTRUCTIONS_PER_GENERATOR) -> InstructionLibrary:
    """Builds a small in-memory instruction library covering pulse/triangle/noise."""
    window = Window.from_config(config)
    extractor = get_feature_extractor(config, window)
    generators = get_generators_by_names(config, LIBRARY_GENERATORS)

    data: Dict[InstructionUnion, InstructionLibraryFragment[Any]] = {}
    for generator in generators.values():
        for instruction in list(generator.get_possible_instructions())[:per_generator]:
            data[instruction] = InstructionLibraryFragment.create(generator, instruction, extractor)

    library = InstructionLibrary()
    library.data[library.create_key(config, window)] = InstructionLibraryData.create(config, data)
    return library


def reconstruct_sample(
    audio: np.ndarray,
    config: Config,
    library: InstructionLibrary,
    *,
    tmp_dir: Pathlike,
    name: str,
) -> Reconstruction:
    """Runs the real reconstruction pipeline on ``audio`` via a temp WAV."""
    path = Path(tmp_dir) / f"{name}.wav"
    write_wave(path, config.library.sample_rate, audio)
    reconstruction = Reconstructor(config, library=library)(path)
    if reconstruction is None:
        raise AssertionError(f"Reconstruction of '{name}' produced no result")
    return reconstruction


def make_sample(
    name: str,
    audio: np.ndarray,
    config: Config,
    library: InstructionLibrary,
    *,
    tmp_dir: Pathlike,
    expected_slices: FrozenSet[GeneratorName],
    loop: bool = False,
) -> Sample:
    """Reconstructs ``audio`` into a `Sample`, asserting the covered channel slices."""
    reconstruction = reconstruct_sample(audio, config, library, tmp_dir=tmp_dir, name=name)
    covered = frozenset(reconstruction.instructions)
    if covered != expected_slices:
        raise AssertionError(f"Sample '{name}' covers {set(covered)}, expected {set(expected_slices)}")
    return Sample(name=name, reconstruction=reconstruction, loop=loop)
