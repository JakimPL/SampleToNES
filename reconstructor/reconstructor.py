from typing import Any, Dict, List, Optional

import numpy as np

from config import Config
from ffts.window import Window
from library.fragment import FragmentedAudio
from library.library import Library, LibraryData
from reconstructor.approximation import ApproximationData
from reconstructor.maps import GENERATOR_CLASSES, MIXER_LEVELS
from reconstructor.reconstruction import Reconstruction
from reconstructor.state import ReconstructionState
from reconstructor.worker import ReconstructorWorker
from typehints.generators import GeneratorUnion
from utils import parallelize


class Reconstructor:
    def __init__(self, config: Config, generator_names: Optional[List[str]] = None) -> None:
        self.config: Config = config
        self.state: ReconstructionState = ReconstructionState.create([])

        default_generators = list(GENERATOR_CLASSES.keys())
        generator_names = generator_names or default_generators
        self.generators: Dict[str, GeneratorUnion] = {
            name: GENERATOR_CLASSES[name](config, name) for name in generator_names
        }

        self.window: Window = Window(config)
        self.library_data: LibraryData = self.load_library()

    def __call__(self, audio: np.ndarray) -> Reconstruction:
        self.reset_generators()
        self.state = ReconstructionState.create(list(self.generators.keys()))
        coefficient = np.max(np.abs(audio)) / sum(
            MIXER_LEVELS[generator.class_name()] for generator in self.generators.values()
        )

        fragmented_audio = self.get_fragments(audio / coefficient)
        self.reconstruct(fragmented_audio)
        return Reconstruction.from_results(self.state, self.config)

    def get_fragments(self, audio: np.ndarray) -> FragmentedAudio:
        return FragmentedAudio.create(audio, self.window)

    def reconstruct(self, fragmented_audio: FragmentedAudio) -> None:
        fragments_ids = fragmented_audio.fragments_ids
        if self.config.max_workers > 1:

            def function(fragments_ids: List[int]) -> Dict[int, Any]:
                worker = ReconstructorWorker(
                    config=self.config,
                    window=self.window,
                    generators=self.generators,
                    library_data=self.library_data,
                )

                return worker(fragmented_audio, fragments_ids)

            results = parallelize(function, fragments_ids, max_workers=self.config.max_workers)
        else:
            worker = ReconstructorWorker(
                config=self.config,
                window=self.window,
                generators=self.generators,
                library_data=self.library_data,
            )
            results = worker(fragmented_audio, fragments_ids, show_progress=True)

        sorted_results = dict(sorted(results.items()))
        for fragment_approximation in sorted_results.values():
            self.update_state(fragment_approximation)

    def load_library(self) -> LibraryData:
        library = Library.load()
        library_data = library.get(self.config, self.window)
        return LibraryData(data=library_data.filter({generator.class_name() for generator in self.generators.values()}))

    def update_state(self, fragment_approximation: ApproximationData) -> None:
        self.state.append(fragment_approximation)

    def reset_generators(self) -> None:
        for generator in self.generators.values():
            generator.reset()
