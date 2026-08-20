from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np

from sampletones_core.audio import active_frame_level, load_audio, mix_audios
from sampletones_core.configs import Config
from sampletones_core.constants.algorithm import MINIMUM_AUDIO_LEVEL
from sampletones_core.constants.enums import ChannelName
from sampletones_core.fft import FragmentedAudio, Window
from sampletones_core.generators import (
    MIXER_LEVELS,
    GeneratorUnion,
    get_generators_by_channels,
)
from sampletones_core.library import InstructionLibrary, InstructionLibraryData
from sampletones_core.reconstructions.reconstruction.reconstruction import Reconstruction
from sampletones_core.reconstructions.reconstruction.stems.channel_assignment import ChannelAssignment
from sampletones_core.reconstructions.reconstruction.stems.data import StemsData
from sampletones_core.reconstructions.reconstructor.approximation import ApproximationData
from sampletones_core.reconstructions.reconstructor.selector.matching import FrameMatcher
from sampletones_core.reconstructions.reconstructor.state import ReconstructionState
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.stem import Stem
from sampletones_core.reconstructions.reconstructor.stems.frame import assign_frame
from sampletones_core.reconstructions.reconstructor.stems.models.hierarchy import StemHierarchy
from sampletones_core.reconstructions.reconstructor.worker import ReconstructorWorker
from sampletones_shared.exceptions import NoLibraryDataError
from sampletones_shared.types.path import Pathlike
from sampletones_shared.utils.system.paths import to_path


def reconstruct(
    fragments_ids: List[int],
    fragmented_audio: FragmentedAudio,
    config: Config,
    window: Window,
    channels: Dict[ChannelName, GeneratorUnion],
    library_data: InstructionLibraryData,
) -> Dict[int, Dict[ChannelName, ApproximationData]]:
    """Reconstructs the given fragments in a single worker pass.

    Args:
        fragments_ids: Indices of the fragments to reconstruct.
        fragmented_audio: The framed target audio.
        config: The reconstruction configuration.
        window: The analysis window.
        channels: The channels to match against, each carrying its generator.
        library_data: The instruction library the candidates are drawn from.

    Returns:
        For each fragment id, the chosen approximation per channel.
    """
    worker = ReconstructorWorker(
        config=config,
        window=window,
        channels=channels,
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
            config: The reconstruction configuration selecting channels, window, and
                matching settings.
            library: The instruction library to match against; a default library rooted
                at the configured directory is used when omitted.

        Raises:
            NoLibraryDataError: If no library exists for the configuration and window.
        """
        self.config: Config = config
        self.state: ReconstructionState = ReconstructionState.create([])

        channel_names = self.config.generation.channels
        self.channels = get_generators_by_channels(config, channel_names)

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
        self.state = ReconstructionState.create(list(self.channels.keys()))
        coefficient = self.get_coefficient(audio)
        fragmented_audio = self.get_fragments(audio / coefficient)
        self.reconstruct(fragmented_audio)
        return Reconstruction.from_state(self.state, self.config, coefficient, path)

    # TODO: refactor: split into steps so this function reads as prose
    # each step should be a separate function that has a single concrete objective
    def reconstruct_stems(
        self,
        paths: Sequence[Pathlike],
        stems_config: StemsConfig,
    ) -> Optional[Reconstruction]:
        """Reconstructs the mix of several stem audio files into one reconstruction.

        Loads and normalizes every stem, matches the frames of the stems' mix against
        the library, and assigns each frame's channels to the stems following the
        configured hierarchy and channel cap. The per-frame assignment is recorded in
        the reconstruction's stems data.

        Args:
            paths: Paths to the stem audio files, one per stems entry.
            stems_config: The stems setup built for this process from the inputs:
                the entries with their channels, the precedence hierarchy, and the
                per-stem channel cap.

        Returns:
            Optional[Reconstruction]: The reconstruction built from the mix.

        Raises:
            ValueError: If the entries count differently than ``paths``.
            TypeError: If a path is not a string or ``Path``.
        """
        if len(paths) != len(stems_config.entries):
            raise ValueError(f"Expected {len(stems_config.entries)} stem paths, got {len(paths)}")

        checked_paths: List[Path] = []
        for path in paths:
            if not isinstance(path, (str, Path)):
                raise TypeError("Input must be a path to an audio file")
            checked_paths.append(to_path(path))

        audios = [self.load_audio(path) for path in checked_paths]
        mix = mix_audios(audios)
        coefficient = self.get_coefficient(mix)
        self.reset_generators()
        covered = {channel for entry in stems_config.entries for channel in entry.channels}
        self.state = ReconstructionState.create([name for name in ChannelName.items() if name in covered])
        fragmented_audio = self.get_fragments(mix / coefficient)

        worker = ReconstructorWorker(
            config=self.config,
            window=self.window,
            channels=self.channels,
            library_data=self.library_data,
            signal_length=mix.shape[0],
        )
        matcher = FrameMatcher(
            config=worker.config,
            candidate_provider=worker.candidate_provider,
            scorer=worker.scorer,
            phase_aligner=worker.phase_aligner,
        )
        stems = {
            entry.id: Stem(
                id=entry.id,
                channels=frozenset(entry.channels),
            )
            for entry in stems_config.entries
        }
        hierarchy = StemHierarchy(
            levels=tuple(tuple(level) for level in stems_config.hierarchy.levels),
            mode=stems_config.hierarchy.mode,
        )

        assignments: Dict[ChannelName, List[int]] = {}
        for fragment_id in fragmented_audio.fragments_ids:
            fragment = fragmented_audio[fragment_id]
            frame_assignment = assign_frame(
                fragment,
                stems,
                hierarchy,
                self.channels,
                matcher,
                worker.feature_extractor,
                stems_config.channel_cap,
            )
            for choice in frame_assignment.choices:
                self.update_state(
                    ApproximationData(
                        channel_name=choice.channel_name,
                        approximation=choice.approximation,
                        instruction=choice.instruction,
                    )
                )
                assignments.setdefault(choice.channel_name, []).append(choice.stem_id)

        stems_data = StemsData(
            config=stems_config,
            assignments=[
                ChannelAssignment(
                    channel_name=channel,
                    stem_ids=stem_ids,
                )
                for channel, stem_ids in assignments.items()
            ],
        )
        return Reconstruction.from_state(
            self.state,
            self.config,
            coefficient,
            tuple(checked_paths),
            stems_data=stems_data,
        )

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
        total = sum(MIXER_LEVELS[generator.class_name()] for generator in self.channels.values())
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
            channels=self.channels,
            library_data=self.library_data,
            signal_length=fragmented_audio.audio.shape[0],
        )

        results = worker(fragmented_audio, fragments_ids)
        for fragment_approximations in results.values():
            for fragment_approximation in fragment_approximations.values():
                self.update_state(fragment_approximation)

    def load_library(self, library: Optional[InstructionLibrary] = None) -> InstructionLibraryData:
        """Loads and filters the instruction library for the enabled channels.

        Args:
            library: The library to draw from; a default library rooted at the
                configured directory is used when omitted.

        Returns:
            InstructionLibraryData: The library data restricted to the enabled
                channels' instruction types.

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
                tuple(generator.class_name() for generator in self.channels.values()),
            ),
        )

    def update_state(self, fragment_approximation: ApproximationData) -> None:
        """Appends one fragment's chosen approximation to the reconstruction state.

        Regenerates the approximation from its instruction when final regeneration is
        enabled, otherwise reuses the stored approximation, scaling either by the
        configured drive.

        Args:
            fragment_approximation: The chosen approximation for one fragment and
                channel.
        """
        generator: GeneratorUnion = self.channels[fragment_approximation.channel_name]
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
        """Resets every channel's generator so the next reconstruction starts fresh."""
        for generator in self.channels.values():
            generator.reset()
