from dataclasses import dataclass
from pathlib import Path
from typing import AbstractSet, Dict, Final, Iterator, List, Optional, Sequence, Tuple

import numpy as np

from sampletones_core.audio import (
    common_length,
    mix,
    mix_scale,
    read_stems,
    scale_stems,
)
from sampletones_core.configs import Config
from sampletones_core.configs.generation import PASSES_HEARD_ALONE
from sampletones_core.constants.enums import ChannelName, ordered_channels
from sampletones_core.fft import Fragment, FragmentedAudio, Window
from sampletones_core.fft.layers import analysis_layers
from sampletones_core.generators import get_generators_by_channels
from sampletones_core.library import InstructionLibrary, InstructionLibraryData
from sampletones_core.reconstructions.progress import (
    FRAMES_PREPARED,
    PREPARATIONS,
    RECORDINGS_LOADED,
    STAGE_BEGUN,
    WHOLE_STAGE,
    ReconstructionReporter,
    announce,
)
from sampletones_core.reconstructions.reconstruction.reconstruction import (
    Reconstruction,
)
from sampletones_core.reconstructions.reconstruction.stems.channel_assignment import (
    ChannelAssignment,
)
from sampletones_core.reconstructions.reconstruction.stems.data import StemsData
from sampletones_core.reconstructions.reconstructor.decoder.base import Streams
from sampletones_core.reconstructions.reconstructor.decoder.transition import (
    TransitionWeights,
)
from sampletones_core.reconstructions.reconstructor.level.working import (
    WorkingLevel,
    WorkingLevelFactory,
    working_level,
)
from sampletones_core.reconstructions.reconstructor.matching import FrameMatcher
from sampletones_core.reconstructions.reconstructor.observer import (
    SILENT_OBSERVER,
    ReconstructionObserver,
)
from sampletones_core.reconstructions.reconstructor.refinement import PitchRefiner
from sampletones_core.reconstructions.reconstructor.state import ReconstructionState
from sampletones_core.reconstructions.reconstructor.stems.assignment.assigners import (
    frame_assigner,
)
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.assigner import (
    JointAssigner,
)
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.neighbors import (
    NeighborPass,
)
from sampletones_core.reconstructions.reconstructor.stems.assignment.track import (
    TrackAssignment,
)
from sampletones_core.reconstructions.reconstructor.stems.configs.config import (
    StemsConfig,
)
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import (
    StemSettings,
)
from sampletones_core.reconstructions.reconstructor.window.profiles import (
    frame_profiles,
)
from sampletones_core.reconstructions.reconstructor.worker import ReconstructorWorker
from sampletones_core.reconstructions.stage import ReconstructionStage
from sampletones_shared.exceptions import NoLibraryDataError
from sampletones_shared.types.path import Pathlike
from sampletones_shared.utils.progress import silent_reporter
from sampletones_shared.utils.system.paths import to_path

HEARD_ALONE_PASS: Final[int] = 0
CONFIGURED_WORKING_LEVEL: Final[WorkingLevelFactory] = working_level  # pylint: disable=invalid-name


@dataclass(frozen=True)
class LoadedStems:
    """Each stem's recording on the shared scale, and the factor that scale divided them by.

    The factor is measured on the whole set a conversion reads, so the document records it and
    reads the recordings that stay at that same level once one of them leaves.

    Attributes:
        recordings: Each stem's recording, in entry order.
        scale: The factor every recording was divided by.
    """

    recordings: Tuple[np.ndarray, ...]
    scale: float


@dataclass(frozen=True)
class PreparedStems:
    """Each stem's recording at the level the matching is made on, and the frames it was cut into.

    The matching reads the frames and the refinement reads the recording they came from, so both
    travel together from the one place that scales them.

    Attributes:
        recordings: Each stem's scaled recording, keyed by stem id.
        frames: Each stem's frames, keyed by stem id.
        coefficient: The factor the whole set was scaled by.
    """

    recordings: Dict[int, np.ndarray]
    frames: Dict[int, FragmentedAudio]
    coefficient: float


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
        channels: AbstractSet[ChannelName],
        library: Optional[InstructionLibrary] = None,
        *,
        level_factory: WorkingLevelFactory = CONFIGURED_WORKING_LEVEL,
    ) -> None:
        """Builds a reconstructor for a configuration and loads its library.

        Args:
            config: The reconstruction configuration selecting the window and the matching
                settings.
            channels: The channels this run hands out, which it builds generators for.
            library: The instruction library to match against; a default library rooted
                at the configured directory is used when omitted.
            level_factory: Builds the working level every run matches at, by default the one
                ``config.general.level`` names.

        Raises:
            NoLibraryDataError: If no library exists for the configuration and window.
        """
        self.config: Config = config
        self.state: ReconstructionState = ReconstructionState.create([])

        self.channel_names: List[ChannelName] = ordered_channels(channels)
        self.channels = get_generators_by_channels(config, self.channel_names)

        self.window: Window = Window.from_config(self.config)
        self.level: WorkingLevel = level_factory(self.config, self.channels, self.window)
        self.library_data: InstructionLibraryData = self.load_library(library)
        self.layer_data: Tuple[InstructionLibraryData, ...] = self.load_layer_libraries(library)

    def __call__(
        self,
        path: Pathlike,
        *,
        observe: ReconstructionObserver = SILENT_OBSERVER,
    ) -> Optional[Reconstruction]:
        """Reconstructs an audio file into a :class:`Reconstruction`.

        The classic run is the stems pipeline's single-stem case: one stem covering
        every channel this reconstructor was built for, on one precedence level,
        sounding all of them at once, so every one of them is assigned in every frame.

        Args:
            path: Path to the audio file to reconstruct.
            observe: Hears the columns and pools the last assignment offered and the streams decoded from them.

        Returns:
            Optional[Reconstruction]: The reconstruction built from the file.

        Raises:
            TypeError: If ``path`` is not a string or ``Path``.
        """
        stems_config = StemsConfig.single_entry(StemSettings.covering(list(self.channel_names)))
        return self.reconstruct([path], stems_config, observe=observe)

    def reconstruct(
        self,
        paths: Sequence[Pathlike],
        stems_config: StemsConfig,
        *,
        report: ReconstructionReporter = silent_reporter,
        observe: ReconstructionObserver = SILENT_OBSERVER,
    ) -> Optional[Reconstruction]:
        """Reconstructs one or more stem audio files into one reconstruction.

        Loads the stems onto one scale drawn from their mix, matches each stem's frames
        against the library on its own, and assigns each frame's channels to the stems
        following the configured hierarchy and each stem's own count. A stem takes a channel where
        its own recording sounds, so what the channel carries is that recording, at the drive that
        stem's settings give the channel. The assignment leaves every channel in play a column of
        candidates per frame, which the configured decoder reads into the stream that channel plays.
        The per-frame assignment is recorded in the reconstruction's stems data.

        Args:
            paths: Paths to the stem audio files, one per stems entry.
            stems_config: The stems setup built for this process from the inputs:
                the entries with what each recording is converted with, and the
                precedence hierarchy.
            report: Hears each stage of the run and answers whether it is still wanted.
            observe: Hears the columns and pools the last assignment offered and the streams decoded from them.

        Returns:
            Optional[Reconstruction]: The reconstruction built from the stems.

        Raises:
            ValueError: If the entries count differently than ``paths``.
            TypeError: If a path is not a string or ``Path``.
            OperationCanceled: If the run is withdrawn while it is under way.
        """
        checked_paths = self._check_stem_paths(paths, stems_config)
        loaded, prepared, worker = self._prepare_run(checked_paths, stems_config, report)
        assignment, streams = self._decide(prepared.frames, stems_config, worker, report)
        observe.assigned(assignment.alternatives)
        observe.decoded(streams)
        self._play(assignment, streams, stems_config, prepared.recordings, report)
        return Reconstruction.from_state(
            self.state,
            self.config,
            prepared.coefficient,
            tuple(checked_paths),
            stems_data=self._build_stems_data(stems_config, assignment.stem_ids, loaded.scale),
        )

    def _prepare_run(
        self,
        checked_paths: List[Path],
        stems_config: StemsConfig,
        report: ReconstructionReporter,
    ) -> Tuple[LoadedStems, PreparedStems, ReconstructorWorker]:
        """Loads the recordings, builds the matching machinery for their length and frames them at the working level.

        Returns:
            The loaded recordings, their frames at the working level and the machinery they are matched with.
        """
        announce(report, ReconstructionStage.LOADING, STAGE_BEGUN, PREPARATIONS)
        loaded = self._load_stem_recordings(checked_paths)
        announce(report, ReconstructionStage.LOADING, RECORDINGS_LOADED, PREPARATIONS)
        worker = self._build_worker(common_length(loaded.recordings))
        prepared = self._prepare_stem_frames(loaded.recordings, stems_config, worker.matcher)
        announce(report, ReconstructionStage.LOADING, FRAMES_PREPARED, PREPARATIONS)
        return loaded, prepared, worker

    def _decide(
        self,
        stem_frames: Dict[int, FragmentedAudio],
        stems_config: StemsConfig,
        worker: ReconstructorWorker,
        report: ReconstructionReporter,
    ) -> Tuple[TrackAssignment, Streams]:
        """The frames' assignment and the streams decoded from it.

        Every frame is first assigned heard alone. Each configured neighbor pass decodes the assignment
        before it and assigns every frame again among what that decode plays around it. The last
        assignment is decoded into the streams the run plays, so the assignment returned is the one its
        streams were decoded from. The decodes between the passes run within matching's span, and
        decoding begins with the last decode, so the progress a run reports only moves forward.
        """
        assignment = self._assign_stem_frames(stem_frames, stems_config, worker, report)
        for pass_index in range(PASSES_HEARD_ALONE, self.config.generation.assignment.passes):
            streams = worker.decoder.decode(assignment.alternatives)
            assignment = self._assign_beside_neighbors(stem_frames, stems_config, worker, streams, pass_index, report)

        announce(report, ReconstructionStage.DECODING, STAGE_BEGUN, WHOLE_STAGE)
        return assignment, worker.decoder.decode(assignment.alternatives)

    def _play(
        self,
        assignment: TrackAssignment,
        streams: Streams,
        stems_config: StemsConfig,
        recordings: Dict[int, np.ndarray],
        report: ReconstructionReporter,
    ) -> None:
        """Hands the frames the decode left silent back to rest, refines every note's pitch and records the streams."""
        assignment.release_silent(streams)
        refined = self._refiner(stems_config).refine(streams, assignment.stem_ids, recordings)
        announce(report, ReconstructionStage.DECODING, WHOLE_STAGE, WHOLE_STAGE)
        self._record_streams(refined, report)

    def _refiner(self, stems_config: StemsConfig) -> PitchRefiner:
        """The pass that carries each chosen note toward the fundamental the recording sounds."""
        return PitchRefiner(config=self.config, channels=self.channels, stems=stems_config)

    @staticmethod
    def _check_stem_paths(
        paths: Sequence[Pathlike],
        stems_config: StemsConfig,
    ) -> List[Path]:
        """Validates the stem paths against the entries and converts them to absolute ``Path`` objects.

        An absolute path keeps the recording reachable from any working directory the
        reconstruction is later opened in.

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

            checked_paths.append(to_path(path).absolute())

        return checked_paths

    def _load_stem_recordings(self, checked_paths: List[Path]) -> LoadedStems:
        """Loads the recordings onto the one scale and length the run measures them on.

        The set is scaled by the peak of its own mix, so each recording keeps the level it
        holds there and the mix is the balance the recordings were captured in. The scale is
        measured on every recording the run reads, before any of them leaves the result.
        """
        general = self.config.general
        recordings = read_stems(checked_paths, target_sample_rate=self.config.library.sample_rate)
        scale = mix_scale(recordings, normalize=general.normalize)
        return LoadedStems(
            recordings=scale_stems(
                recordings,
                scale=scale,
                quantize=general.quantize,
                quantization_levels=general.quantization_levels,
            ),
            scale=scale,
        )

    def _prepare_stem_frames(
        self,
        recordings: Sequence[np.ndarray],
        stems_config: StemsConfig,
        matcher: FrameMatcher,
    ) -> PreparedStems:
        """Scales the recordings to the working level and frames each of them.

        The working level reads every recording at once, so one factor scales the whole set and
        a recording quieter than the mix reaches its frames at the level it holds there.
        Framing every recording on its own is what lets a stem's picks be scored against
        the sound that stem contributes.

        Args:
            recordings: The loaded stem recordings, in entry order.
            stems_config: The stems setup the run is made under.
            matcher: The matching machinery the working level may read the recordings with.

        Returns:
            PreparedStems: The scaled recordings and their frames, keyed by stem id, together
                with the coefficient they were scaled by.
        """
        coefficient = self.level.coefficient(recordings, stems_config, matcher)
        self.reset_generators()
        covered = stems_config.covered_channels
        self.state = ReconstructionState.create([name for name in ChannelName.items() if name in covered])
        scaled = {entry.id: recording / coefficient for entry, recording in zip(stems_config.entries, recordings)}
        return PreparedStems(
            recordings=scaled,
            frames={stem_id: self.get_fragments(recording) for stem_id, recording in scaled.items()},
            coefficient=coefficient,
        )

    def _build_worker(self, signal_length: int) -> ReconstructorWorker:
        """Builds the matching machinery and the decoder this recording runs through."""
        return ReconstructorWorker(
            config=self.config,
            window=self.window,
            channels=self.channels,
            library_data=self.library_data,
            layer_data=self.layer_data,
            signal_length=signal_length,
        )

    def _assign_stem_frames(
        self,
        stem_frames: Dict[int, FragmentedAudio],
        stems_config: StemsConfig,
        worker: ReconstructorWorker,
        report: ReconstructionReporter,
    ) -> TrackAssignment:
        """Assigns every frame's channels to the stems, each frame heard alone, and gathers the outcome per channel.

        Every stem hands the assignment the same frame of its own recording, so a pick is
        judged against what that stem sounds there. Each frame answers every channel in play
        — a pick or a rest — so the lattices the decoder reads and the per-channel stem record
        stay parallel to the frames, and stem id ``i`` names frame ``i`` of its channel.
        """
        assignment = TrackAssignment(self.state.channel_names)
        assigner = frame_assigner(
            self.config.generation.assignment.method,
            stems_config,
            self.channels,
            worker.matcher,
            worker.decoder.lattice_width,
        )
        for frame in self._frames_announced(stem_frames, HEARD_ALONE_PASS, report):
            assignment.add(assigner.assign(self._frames_at(stem_frames, frame)))

        return assignment

    def _assign_beside_neighbors(
        self,
        stem_frames: Dict[int, FragmentedAudio],
        stems_config: StemsConfig,
        worker: ReconstructorWorker,
        streams: Streams,
        pass_index: int,
        report: ReconstructionReporter,
    ) -> TrackAssignment:
        """Assigns every frame again, in turn, among the notes ``streams`` plays around it, in pass ``pass_index``.

        A frame's analysis window reads its neighbors too, so what they play is a fixed part of the
        frame's reading, as a :class:`NeighborPass` hears it. A recording of no frames assigns none.
        """
        assignment = TrackAssignment(self.state.channel_names)
        if not self._stem_frame_count(stem_frames):
            return assignment

        neighbor_pass = NeighborPass.over(
            JointAssigner(stems_config, self.channels, worker.matcher, worker.decoder.lattice_width),
            streams,
            frame_profiles(self.config, self.window, worker.candidate_provider.sizes),
            TransitionWeights.of(self.config),
            self.config.generation.assignment.inertia,
        )
        for frame in self._frames_announced(stem_frames, pass_index, report):
            assignment.add(neighbor_pass.assign(frame, self._frames_at(stem_frames, frame)))

        return assignment

    def _frames_announced(
        self, stem_frames: Dict[int, FragmentedAudio], pass_index: int, report: ReconstructionReporter
    ) -> Iterator[int]:
        """Every frame the recordings share, in order, announced as pass ``pass_index`` reaches it and at its end.

        Matching counts the frames of every pass the run makes, so a pass counts on from the frames of
        the passes before it, and the count rises through the whole of matching.
        """
        frames = self._stem_frame_count(stem_frames)
        matched = pass_index * frames
        total = self.config.generation.assignment.passes * frames
        for frame in range(frames):
            announce(report, ReconstructionStage.MATCHING, matched + frame, total)
            yield frame

        announce(report, ReconstructionStage.MATCHING, matched + frames, total)

    @staticmethod
    def _frames_at(stem_frames: Dict[int, FragmentedAudio], frame: int) -> Dict[int, Fragment]:
        """Frame ``frame`` of every stem's recording, keyed by stem id."""
        return {stem_id: fragments[frame] for stem_id, fragments in stem_frames.items()}

    @staticmethod
    def _stem_frame_count(stem_frames: Dict[int, FragmentedAudio]) -> int:
        """The frames every recording answers, which they share by sharing a length."""
        return min((len(fragments) for fragments in stem_frames.values()), default=0)

    def _record_streams(
        self,
        streams: Streams,
        report: ReconstructionReporter,
    ) -> None:
        """Reads the decoded streams into the state, one frame at a time.

        A reconstruction records the instructions its channels play, and reads its sound from
        them, so this is where a run's answer is gathered.
        """
        frames = self._frame_count(streams)
        for position in range(frames):
            announce(report, ReconstructionStage.GATHERING, position, frames)
            for channel_name in self.state.channel_names:
                self.state.append(channel_name, streams[channel_name][position].instruction)

        announce(report, ReconstructionStage.GATHERING, frames, frames)

    @staticmethod
    def _frame_count(streams: Streams) -> int:
        """The frames the streams span; every channel in play answers each of them."""
        return max((len(stream) for stream in streams.values()), default=0)

    @staticmethod
    def _build_stems_data(
        stems_config: StemsConfig,
        assignments: Dict[ChannelName, List[int]],
        scale: float,
    ) -> StemsData:
        """Assembles the per-channel per-frame stem record into serializable stems data."""
        return StemsData(
            config=stems_config,
            assignments=tuple(
                ChannelAssignment(channel_name=channel, stem_ids=tuple(stem_ids))
                for channel, stem_ids in assignments.items()
            ),
            scale=scale,
        )

    def load_audio(self, paths: Sequence[Path]) -> np.ndarray:
        """The recordings at ``paths``, mixed, at the level a conversion of them together matches against.

        They are read through the very loading a conversion reads its recordings by, so a referee
        comparing a reconstruction with them hears the level the conversion matched. One path reads
        that one recording.

        Args:
            paths: Paths to the audio files.

        Returns:
            np.ndarray: The prepared mix.
        """
        return mix(list(self._load_stem_recordings(list(paths)).recordings))

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
        return self._library_of(library or InstructionLibrary.from_config(self.config), self.config, self.window)

    def load_layer_libraries(self, library: Optional[InstructionLibrary] = None) -> Tuple[InstructionLibraryData, ...]:
        """Loads the library of every spectrum method ``generation.layers`` adds, each for the enabled channels.

        Args:
            library: The instruction library to draw from; a default library rooted at the
                configured directory is used when omitted.

        Returns:
            One library per added method, in the order the configuration adds them.

        Raises:
            NoLibraryDataError: If an added method's library is missing.
        """
        source = library or InstructionLibrary.from_config(self.config)
        return tuple(self._library_of(source, layer.config, layer.window) for layer in analysis_layers(self.config)[1:])

    def _library_of(self, library: InstructionLibrary, config: Config, window: Window) -> InstructionLibraryData:
        """The library ``config`` and ``window`` select from ``library``, restricted to the enabled channels.

        Raises:
            NoLibraryDataError: If no library exists for the configuration and window.
        """
        library_data = library.get(config, window)
        key = library.create_key(config, window)
        if not library_data:
            raise NoLibraryDataError(
                f"No library data found for the given configuration and window: {library.get_path(key)}"
            )

        return InstructionLibraryData.create(
            config=config,
            data=library_data.filter(
                tuple(generator.class_name() for generator in self.channels.values()),
            ),
        )

    def reset_generators(self) -> None:
        """Resets every channel's generator so the next reconstruction starts fresh."""
        for generator in self.channels.values():
            generator.reset()
