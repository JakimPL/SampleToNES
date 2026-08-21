from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from sampletones_core.audio import active_frame_level, load_audio, mix
from sampletones_core.configs import Config
from sampletones_core.constants.algorithm import MINIMUM_AUDIO_LEVEL
from sampletones_core.constants.enums import ChannelName
from sampletones_core.fft import FragmentedAudio, Window
from sampletones_core.generators import (
    MIXER_LEVELS,
    GeneratorUnion,
    get_generators_by_channels,
)
from sampletones_core.instructions import InstructionUnion
from sampletones_core.library import InstructionLibrary, InstructionLibraryData
from sampletones_core.reconstructions.reconstruction.reconstruction import Reconstruction
from sampletones_core.reconstructions.reconstruction.stems.channel_assignment import ChannelAssignment
from sampletones_core.reconstructions.reconstruction.stems.data import StemsData
from sampletones_core.reconstructions.reconstructor.decoder.base import Streams
from sampletones_core.reconstructions.reconstructor.state import ReconstructionState
from sampletones_core.reconstructions.reconstructor.stems.assignment.frame import assign_frame
from sampletones_core.reconstructions.reconstructor.stems.assignment.track import TrackAssignment
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.worker import ReconstructorWorker
from sampletones_shared.exceptions import NoLibraryDataError
from sampletones_shared.types.path import Pathlike
from sampletones_shared.utils.system.paths import to_path


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

        The classic run is the stems pipeline's single-stem case: one stem covering
        every enabled channel on one precedence level, with the cap at the channel
        count, so every enabled channel is assigned in every frame.

        Args:
            path: Path to the audio file to reconstruct.

        Returns:
            Optional[Reconstruction]: The reconstruction built from the file.

        Raises:
            TypeError: If ``path`` is not a string or ``Path``.
        """
        stems_config = StemsConfig.single_entry(list(self.config.generation.channels))
        return self.reconstruct([path], stems_config)

    def reconstruct(
        self,
        paths: Sequence[Pathlike],
        stems_config: StemsConfig,
    ) -> Optional[Reconstruction]:
        """Reconstructs the mix of one or more stem audio files into one reconstruction.

        Loads and normalizes every stem, matches the frames of the stems' mix against
        the library, and assigns each frame's channels to the stems following the
        configured hierarchy and channel cap. The assignment leaves every channel in
        play a column of candidates per frame, which the configured decoder reads into
        the stream that channel plays. The per-frame assignment is recorded in the
        reconstruction's stems data.

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
        checked_paths = self._check_stem_paths(paths, stems_config)
        mixed = self._mix_stem_audios(checked_paths)
        fragmented_audio, coefficient = self._prepare_stem_frames(mixed, stems_config)
        worker = self._build_worker(mixed)
        assignment = self._assign_stem_frames(fragmented_audio, stems_config, worker)
        self._drop_resting_channels(assignment)
        self._record_streams(worker.decoder.decode(assignment.lattices))
        return Reconstruction.from_state(
            self.state,
            self.config,
            coefficient,
            tuple(checked_paths),
            stems_data=self._build_stems_data(stems_config, assignment.stem_ids),
        )

    @staticmethod
    def _check_stem_paths(
        paths: Sequence[Pathlike],
        stems_config: StemsConfig,
    ) -> List[Path]:
        """Validates the stem paths against the entries and converts them to ``Path``.

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

        return checked_paths

    def _mix_stem_audios(self, checked_paths: List[Path]) -> np.ndarray:
        """Loads every stem and returns their mix, the target the frames match against."""
        audios = [self.load_audio(path) for path in checked_paths]
        return mix(audios)

    def _prepare_stem_frames(
        self,
        mixed: np.ndarray,
        stems_config: StemsConfig,
    ) -> Tuple[FragmentedAudio, float]:
        """Scales the mix to the working level and frames it over the stems' channels.

        Returns the framed target together with the coefficient it was scaled by, so
        the assembled reconstruction records the level it was matched at.
        """
        coefficient = self.get_coefficient(mixed, stems_config)
        self.reset_generators()
        covered = stems_config.covered_channels
        self.state = ReconstructionState.create([name for name in ChannelName.items() if name in covered])
        return self.get_fragments(mixed / coefficient), coefficient

    def _build_worker(self, signal: np.ndarray) -> ReconstructorWorker:
        """Builds the matching machinery and the decoder this recording runs through."""
        return ReconstructorWorker(
            config=self.config,
            window=self.window,
            channels=self.channels,
            library_data=self.library_data,
            signal_length=signal.shape[0],
        )

    def _assign_stem_frames(
        self,
        fragmented_audio: FragmentedAudio,
        stems_config: StemsConfig,
        worker: ReconstructorWorker,
    ) -> TrackAssignment:
        """Assigns every frame's channels to the stems and gathers the outcome per channel.

        Each frame answers every channel in play — a pick or a rest — so the lattices the
        decoder reads and the per-channel stem record stay parallel to the frames, and stem
        id ``i`` names frame ``i`` of its channel.
        """
        assignment = TrackAssignment(self.state.channel_names)
        for fragment_id in fragmented_audio.fragments_ids:
            assignment.add(
                assign_frame(
                    fragmented_audio[fragment_id],
                    stems_config,
                    self.channels,
                    worker.matcher,
                    worker.feature_extractor,
                    worker.decoder.lattice_width,
                )
            )

        return assignment

    def _drop_resting_channels(self, assignment: TrackAssignment) -> None:
        """Leaves the channels that sound, releasing those that rested through every frame.

        A channel no stem ever took describes nothing, so it stands by: the state releases its
        stream and the record names it no more, which is what keeps a silent channel out of
        every export.
        """
        for channel_name in assignment.resting_channels:
            self.state.drop(channel_name)
            assignment.drop(channel_name)

    def _record_streams(self, streams: Streams) -> None:
        """Folds the decoded streams into the state, one frame at a time.

        Frame order is what carries a generator's oscillator phase from one frame into the
        next, which is the continuity final regeneration renders against.
        """
        for position in range(self._frame_count(streams)):
            for channel_name in self.state.channel_names:
                candidate = streams[channel_name][position]
                self._record(channel_name, candidate.instruction, candidate.approximation.audio)

    @staticmethod
    def _frame_count(streams: Streams) -> int:
        """The frames the streams span; every channel in play answers each of them."""
        return max((len(stream) for stream in streams.values()), default=0)

    @staticmethod
    def _build_stems_data(
        stems_config: StemsConfig,
        assignments: Dict[ChannelName, List[int]],
    ) -> StemsData:
        """Assembles the per-channel per-frame stem record into serializable stems data."""
        return StemsData(
            config=stems_config,
            assignments=[
                ChannelAssignment(channel_name=channel, stem_ids=stem_ids) for channel, stem_ids in assignments.items()
            ],
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

    def get_coefficient(
        self,
        audio: np.ndarray,
        stems_config: StemsConfig,
    ) -> float:
        """
        Working-level coefficient that scales the input into the range one frame spans.

        The reference anchors to the robust active-frame level using the configured
        percentile and audibility floor, and is floored at `MINIMUM_AUDIO_LEVEL` so
        a fully silent input yields a finite coefficient. The range it is measured against
        is what the setup's frame budget reaches: the loudest mixer weights among the covered
        channels, as many of them as one frame can hold, so a capped run targets a level its
        channels render.

        Args:
            audio: The prepared input audio.
            stems_config: The stems setup the reconstruction runs under.

        Returns:
            float: The positive scale factor the input is divided by before matching.
        """
        total = self._frame_mixer_total(stems_config)
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

    def _frame_mixer_total(self, stems_config: StemsConfig) -> float:
        """The mixer weight one frame reaches: the loudest covered channels, up to the budget."""
        covered = stems_config.covered_channels
        levels = sorted(
            (MIXER_LEVELS[generator.class_name()] for name, generator in self.channels.items() if name in covered),
            reverse=True,
        )
        return sum(levels[: stems_config.frame_budget])

    def get_fragments(self, audio: np.ndarray) -> FragmentedAudio:
        """Frames the audio into the fragments matched against the library.

        Args:
            audio: The scaled input audio.

        Returns:
            FragmentedAudio: The framed audio ready for matching.
        """
        return FragmentedAudio.create(audio, self.config, self.window)

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

    def _record(
        self,
        channel_name: ChannelName,
        instruction: InstructionUnion,
        matched_audio: np.ndarray,
    ) -> None:
        """Appends one frame of one channel to the reconstruction state.

        Regenerates the frame from its instruction when final regeneration is enabled, which
        carries the oscillator's phase into the next frame, otherwise keeps the audio the match
        was made on. Either one is scaled by the configured drive.
        """
        generator: GeneratorUnion = self.channels[channel_name]
        if self.config.generation.final_regeneration:
            approximation = (
                generator(
                    instruction,  # type: ignore[arg-type]
                    initials=generator.initials,
                    save=True,
                )
                * self.config.generation.drive
            )
        else:
            approximation = matched_audio * self.config.generation.drive

        self.state.append(channel_name, instruction, approximation)

    def reset_generators(self) -> None:
        """Resets every channel's generator so the next reconstruction starts fresh."""
        for generator in self.channels.values():
            generator.reset()
