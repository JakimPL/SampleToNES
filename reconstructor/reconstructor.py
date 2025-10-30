from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from configs.config import Config
from ffts.window import Window
from library.fragment import FragmentedAudio
from library.library import Library, LibraryData
from reconstructor.approximation import ApproximationData
from reconstructor.maps import GENERATOR_CLASSES, MIXER_LEVELS
from reconstructor.reconstruction import Reconstruction
from reconstructor.state import ReconstructionState
from reconstructor.worker import ReconstructorWorker
from typehints.general import GeneratorName
from typehints.generators import GeneratorUnion
from utils.audio.io import load_audio
from utils.parallel import parallelize


def reconstruct(
    fragments_ids: List[int],
    fragmented_audio: FragmentedAudio,
    config: Config,
    window: Window,
    generators: Dict[str, GeneratorUnion],
    library_data: LibraryData,
) -> Dict[int, Dict[str, ApproximationData]]:
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
        generator_names: Optional[List[GeneratorName]] = None,
        library: Optional[Library] = None,
    ) -> None:
        self.config: Config = config
        self.state: ReconstructionState = ReconstructionState.create([])

        default_generators = list(GENERATOR_CLASSES.keys())
        generator_names = generator_names or default_generators
        self.generators: Dict[str, Generator] = {
            name: GENERATOR_CLASSES[name](config, name) for name in generator_names
        }

        self.window: Window = Window(config.library)
        self.library_data: LibraryData = self.load_library(library)

    def __call__(self, path: Path) -> Reconstruction:
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
        if self.config.general.max_workers > 1:
            results = parallelize(
                reconstruct,
                fragments_ids,
                max_workers=self.config.general.max_workers,
                fragmented_audio=fragmented_audio,
                config=self.config,
                window=self.window,
                generators=self.generators,
                library_data=self.library_data,
            )

            results = dict(
                sorted(
                    (
                        (fragment_id, fragment_approximation)
                        for partial_results in results
                        for fragment_id, fragment_approximation in partial_results.items()
                    ),
                    key=lambda fragment: fragment[0],
                ),
            )

        else:
            worker = ReconstructorWorker(
                config=self.config,
                window=self.window,
                generators=self.generators,
                library_data=self.library_data,
            )

            results = worker(fragmented_audio, fragments_ids, show_progress=True)

        for fragment_approximations in results.values():
            for fragment_approximation in fragment_approximations.values():
                self.update_state(fragment_approximation)

    def load_library(self, library: Optional[Library] = None) -> LibraryData:
        library = library or Library(directory=self.config.general.library_directory)
        library_data = library.get(self.config, self.window)
        return LibraryData(
            config=self.config.library,
            data=library_data.filter({generator.class_name() for generator in self.generators.values()}),
        )

    def update_state(self, fragment_approximation: ApproximationData) -> None:
        generator = self.generators[fragment_approximation.generator_name]
        instruction = fragment_approximation.instruction
        initials = generator.initials
        approximation = generator(instruction, initials=initials, save=True) * self.config.generation.mixer
        self.state.append(fragment_approximation, approximation)

    def reset_generators(self) -> None:
        for generator in self.generators.values():
            generator.reset()
