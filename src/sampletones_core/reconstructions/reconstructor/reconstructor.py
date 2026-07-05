from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from sampletones_core.audio import active_frame_level, load_audio
from sampletones_core.configs import Config
from sampletones_core.constants.algorithm import MINIMUM_AUDIO_LEVEL
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.fft import FragmentedAudio, Window
from sampletones_core.generators import (
    MIXER_LEVELS,
    GeneratorUnion,
    get_generators_by_names,
)
from sampletones_core.library import InstructionLibrary, InstructionLibraryData
from sampletones_shared.exceptions import NoLibraryDataError
from sampletones_shared.types.path import Pathlike
from sampletones_shared.utils.system.paths import to_path

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
    library_data: InstructionLibraryData,
) -> Dict[int, Dict[GeneratorName, ApproximationData]]:
    worker = ReconstructorWorker(
        config=config,
        window=window,
        generators=generators,
        library_data=library_data,
        signal_length=fragmented_audio.audio.shape[0],
    )

    return worker(fragmented_audio, fragments_ids)


class Reconstructor:
    def __init__(
        self,
        config: Config,
        library: Optional[InstructionLibrary] = None,
    ) -> None:
        self.config: Config = config
        self.state: ReconstructionState = ReconstructionState.create([])

        generator_names = self.config.generation.generators
        self.generators = get_generators_by_names(config, generator_names)

        self.window: Window = Window.from_config(self.config)
        self.library_data: InstructionLibraryData = self.load_library(library)

    def __call__(self, path: Pathlike) -> Optional[Reconstruction]:
        if not isinstance(path, (str, Path)):
            raise TypeError("Input must be a path to an audio file")

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
            quantization_levels=self.config.general.quantization_levels,
        )

    def get_coefficient(self, audio: np.ndarray) -> float:
        """
        Working-level coefficient that scales the input into the range the enabled
        channels span.

        The reference anchors to the robust active-frame level using the configured
        percentile and audibility floor, and is floored at `MINIMUM_AUDIO_LEVEL` so
        a fully silent input yields a finite coefficient.
        """
        total = sum(MIXER_LEVELS[generator.class_name()] for generator in self.generators.values())
        level = max(
            active_frame_level(
                audio,
                self.config.library.frame_length,
                percentile=self.config.general.coefficient_percentile,
                audibility_floor=self.config.general.coefficient_audibility_floor,
            ),
            MINIMUM_AUDIO_LEVEL,
        )
        return float(level / total)

    def get_fragments(self, audio: np.ndarray) -> FragmentedAudio:
        return FragmentedAudio.create(audio, self.config, self.window)

    def reconstruct(self, fragmented_audio: FragmentedAudio) -> None:
        fragments_ids = fragmented_audio.fragments_ids
        worker = ReconstructorWorker(
            config=self.config,
            window=self.window,
            generators=self.generators,
            library_data=self.library_data,
            signal_length=fragmented_audio.audio.shape[0],
        )

        results = worker(fragmented_audio, fragments_ids)
        for fragment_approximations in results.values():
            for fragment_approximation in fragment_approximations.values():
                self.update_state(fragment_approximation)

    def load_library(self, library: Optional[InstructionLibrary] = None) -> InstructionLibraryData:
        library = library or InstructionLibrary(directory=self.config.general.library_directory)
        library_data = library.get(self.config, self.window)
        key = library.create_key(self.config, self.window)
        if not library_data:
            raise NoLibraryDataError(
                f"No library data found for the given configuration and window: {library.get_path(key)}"
            )

        return InstructionLibraryData.create(
            config=self.config,
            data=library_data.filter(
                tuple(generator.class_name() for generator in self.generators.values()),
            ),
        )

    def update_state(self, fragment_approximation: ApproximationData) -> None:
        generator: GeneratorUnion = self.generators[fragment_approximation.generator_name]
        if self.config.generation.final_regeneration:
            instruction = fragment_approximation.instruction
            initials = generator.initials
            approximation = (
                generator(
                    instruction,  # type: ignore[arg-type]
                    initials=initials,
                    save=True,
                )
                * self.config.generation.drive
            )
        else:
            approximation = fragment_approximation.approximation.audio * self.config.generation.drive

        self.state.append(fragment_approximation, approximation)

    def reset_generators(self) -> None:
        for generator in self.generators.values():
            generator.reset()
