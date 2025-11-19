from pathlib import Path
from typing import Dict, List, Optional, Union

import numpy as np

from sampletones.audio import load_audio
from sampletones.configs import Config
from sampletones.constants.enums import GeneratorName
from sampletones.exceptions import NoLibraryDataError
from sampletones.ffts import FragmentedAudio, Window
from sampletones.generators import (
    INSTRUCTION_TO_GENERATOR_MAP,
    MIXER_LEVELS,
    GeneratorUnion,
    get_generators_by_names,
)
from sampletones.instructions import INSTRUCTION_CLASS_MAP
from sampletones.library import Library, LibraryData
from sampletones.utils import to_path

from ..reconstruction.reconstruction import Reconstruction
from .approximation import ApproximationData
from .state import ReconstructionState
from .worker import ReconstructorWorker


def reconstruct(
    fragments_ids: List[int],
    fragmented_audio: FragmentedAudio,
    config: Config,
    window: Window,
    generators: Dict[GeneratorName, GeneratorUnion],
    library_data: LibraryData,
) -> Dict[int, Dict[GeneratorName, ApproximationData]]:
    worker = ReconstructorWorker(
        config=config,
        window=window,
        generators=generators,
        library_data=library_data,
    )

    return worker(fragmented_audio, fragments_ids)


class Reconstructor:
    def __init__(
        self,
        config: Config,
        library: Optional[Library] = None,
    ) -> None:
        self.config: Config = config
        self.state: ReconstructionState = ReconstructionState.create([])

        generator_names = self.config.generation.generators
        self.generators = get_generators_by_names(config, generator_names)

        self.window: Window = Window.from_config(self.config)
        self.library_data: LibraryData = self.load_library(library)

    def __call__(self, path: Union[str, Path]) -> Optional[Reconstruction]:
        if not isinstance(path, (str, Path)):
            raise TypeError("Input must be a path to an audio file.")

        path = to_path(path)
        audio = self.load_audio(path)
        self.reset_generators()
        self.state = ReconstructionState.create(list(self.generators.keys()))
        coefficient = self.get_coefficient(audio)
        fragmented_audio = self.get_fragments(audio / coefficient)
        self.reconstruct(fragmented_audio)
        return Reconstruction.from_state(self.state, self.config, coefficient, path)

    def load_audio(self, path: Path) -> np.ndarray:
        return load_audio(
            path,
            target_sample_rate=self.config.library.sample_rate,
            normalize=self.config.general.normalize,
            quantize=self.config.general.quantize,
        )

    def get_coefficient(self, audio: np.ndarray) -> float:
        return np.max(np.abs(audio)) / sum(
            MIXER_LEVELS[generator.class_name()] for generator in self.generators.values()
        )

    def get_fragments(self, audio: np.ndarray) -> FragmentedAudio:
        return FragmentedAudio.create(audio, self.config, self.window)

    def reconstruct(self, fragmented_audio: FragmentedAudio) -> None:
        fragments_ids = fragmented_audio.fragments_ids
        worker = ReconstructorWorker(
            config=self.config,
            window=self.window,
            generators=self.generators,
            library_data=self.library_data,
        )

        results = worker(fragmented_audio, fragments_ids)
        for fragment_approximations in results.values():
            for fragment_approximation in fragment_approximations.values():
                self.update_state(fragment_approximation)

    def load_library(self, library: Optional[Library] = None) -> LibraryData:
        library = library or Library(directory=self.config.general.library_directory)
        library_data = library.get(self.config, self.window)
        key = library.create_key(self.config, self.window)
        if not library_data:
            raise NoLibraryDataError(
                f"No library data found for the given configuration and window: {library.get_path(key)}"
            )

        return LibraryData.create(
            config=self.config,
            data=library_data.filter(
                tuple(generator.class_name() for generator in self.generators.values()),
            ),
        )

    def update_state(self, fragment_approximation: ApproximationData) -> None:
        generator: GeneratorUnion = self.generators[fragment_approximation.generator_name]
        if self.config.generation.final_regeneration:
            instruction_class = INSTRUCTION_TO_GENERATOR_MAP[
                INSTRUCTION_CLASS_MAP[fragment_approximation.instruction.class_name()]
            ]
            instruction: instruction_class = fragment_approximation.instruction
            initials = generator.initials
            approximation = generator(instruction, initials=initials, save=True) * self.config.generation.mixer
        else:
            approximation = fragment_approximation.approximation.audio * self.config.generation.mixer

        self.state.append(fragment_approximation, approximation)

    def reset_generators(self) -> None:
        for generator in self.generators.values():
            generator.reset()
