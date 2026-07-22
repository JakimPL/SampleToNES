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
    """Reconstructs the given fragments in a single worker pass.

    Args:
        fragments_ids: Indices of the fragments to reconstruct.
        fragmented_audio: The framed target audio.
        config: The reconstruction configuration.
        window: The analysis window.
        generators: The generators to match against, by channel name.
        library_data: The instruction library the candidates are drawn from.

    Returns:
        For each fragment id, the chosen approximation per generator.
    """
    worker = ReconstructorWorker(
        config=config,
        window=window,
        generators=generators,
        library_data=library_data,
        signal_length=fragmented_audio.audio.shape[0],
    )

    return worker(fragmented_audio, fragments_ids)


class Reconstructor:
    """
    Turns an audio file into a :class:`Reconstruction` of NES instructions.

    Given a configuration and an instruction library, the reconstructor loads an audio
    file, splits it into frames, and matches each frame against the library to build a
    per-channel instruction sequence that approximates the input. Call the instance
    with an audio path to run the whole pipeline.

    The matching algorithm — framing, candidate scoring, and instruction selection — is
    described in ``docs/concepts/reconstruction.md``.
    """

    def __init__(
        self,
        config: Config,
        library: Optional[InstructionLibrary] = None,
    ) -> None:
        """Builds a reconstructor for a configuration and loads its library.

        Args:
            config: The reconstruction configuration selecting generators, window, and
                matching settings.
            library: The instruction library to match against; a default library rooted
                at the configured directory is used when omitted.

        Raises:
            NoLibraryDataError: If no library exists for the configuration and window.
        """
        self.config: Config = config
        self.state: ReconstructionState = ReconstructionState.create([])

        generator_names = self.config.generation.generators
        self.generators = get_generators_by_names(config, generator_names)

        self.window: Window = Window.from_config(self.config)
        self.library_data: InstructionLibraryData = self.load_library(library)

    def __call__(self, path: Pathlike) -> Optional[Reconstruction]:
        """Reconstructs an audio file into a :class:`Reconstruction`.

        Loads and normalizes the audio, frames it, matches every frame against the
        library, and assembles the chosen instructions into a reconstruction.

        Args:
            path: Path to the audio file to reconstruct.

        Returns:
            Optional[Reconstruction]: The reconstruction built from the file.

        Raises:
            TypeError: If ``path`` is not a string or ``Path``.
        """
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
        """Loads and preconditions the audio at ``path`` for reconstruction.

        Resamples to the library sample rate and applies the configured normalization
        and quantization.

        Args:
            path: Path to the audio file.

        Returns:
            np.ndarray: The prepared audio.
        """
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

        Args:
            audio: The prepared input audio.

        Returns:
            float: The positive scale factor the input is divided by before matching.
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
        """Frames the audio into the fragments matched against the library.

        Args:
            audio: The scaled input audio.

        Returns:
            FragmentedAudio: The framed audio ready for matching.
        """
        return FragmentedAudio.create(audio, self.config, self.window)

    def reconstruct(self, fragmented_audio: FragmentedAudio) -> None:
        """Matches every fragment and records the chosen instructions in the state.

        Runs the matching worker over all fragments and folds each fragment's chosen
        approximation into the running reconstruction state.

        Args:
            fragmented_audio: The framed target audio to match.
        """
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
        """Loads and filters the instruction library for the enabled generators.

        Args:
            library: The library to draw from; a default library rooted at the
                configured directory is used when omitted.

        Returns:
            InstructionLibraryData: The library data restricted to the enabled
                generators' instruction types.

        Raises:
            NoLibraryDataError: If no library exists for the configuration and window.
        """
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
        """Appends one fragment's chosen approximation to the reconstruction state.

        Regenerates the approximation from its instruction when final regeneration is
        enabled, otherwise reuses the stored approximation, scaling either by the
        configured drive.

        Args:
            fragment_approximation: The chosen approximation for one fragment and
                generator.
        """
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
        """Resets every generator so the next reconstruction starts fresh."""
        for generator in self.generators.values():
            generator.reset()
