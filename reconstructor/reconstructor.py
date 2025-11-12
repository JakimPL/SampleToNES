from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from audio import load_audio
from configs import Config
from constants import GeneratorName
from exceptions.library import NoLibraryDataError
from ffts import Window
from generators import GENERATOR_CLASSES, MIXER_LEVELS, Generator, GeneratorUnion
from library import FragmentedAudio, Library, LibraryData

from .approximation import ApproximationData
from .reconstruction import Reconstruction
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
        self.generators: Dict[GeneratorName, GeneratorUnion] = {
            name: GENERATOR_CLASSES[name](config, name) for name in generator_names
        }

        self.window: Window = Window(config.library)
        self.library_data: LibraryData = self.load_library(library)

    def __call__(self, path: Path) -> Optional[Reconstruction]:
        audio = self.load_audio(path)
        self.reset_generators()
        self.state = ReconstructionState.create(list(self.generators.keys()))
        coefficient = self.get_coefficient(audio)
        fragmented_audio = self.get_fragments(audio / coefficient)
        self.reconstruct(fragmented_audio)
        return Reconstruction.from_results(self.state, self.config, coefficient, path)

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

        results = worker(fragmented_audio, fragments_ids, show_progress=False)
        for fragment_approximations in results.values():
            for fragment_approximation in fragment_approximations.values():
                self.update_state(fragment_approximation)

    def load_library(self, library: Optional[Library] = None) -> LibraryData:
        library = library or Library(directory=self.config.general.library_directory)
        library_data = library.get(self.config, self.window)
        if not library_data:
            raise NoLibraryDataError("No library data found for the given configuration and window.")

        return LibraryData(
            config=self.config.library,
            data=library_data.filter({generator.class_name() for generator in self.generators.values()}),
        )

    def update_state(self, fragment_approximation: ApproximationData) -> None:
        generator: Generator[Any, Any] = self.generators[fragment_approximation.generator_name]
        instruction: Any = fragment_approximation.instruction
        initials = generator.initials
        approximation = generator(instruction, initials=initials, save=True) * self.config.generation.mixer
        self.state.append(fragment_approximation, approximation)

    def reset_generators(self) -> None:
        for generator in self.generators.values():
            generator.reset()
