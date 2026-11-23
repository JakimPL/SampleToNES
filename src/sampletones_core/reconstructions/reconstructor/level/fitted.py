from typing import Dict, Final, List, Mapping, Optional, Sequence

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.fft import FragmentedAudio, Window
from sampletones_core.generators import GeneratorUnion
from sampletones_core.reconstructions.reconstructor.matching import FrameMatcher
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.assigner import JointAssigner
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.catalog import kind_catalogs
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.layout import StemLayout
from sampletones_core.reconstructions.reconstructor.stems.assignment.rests import frame_sounds
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry

from .judgment import ChosenFrame, Judgment
from .line import LevelReading, StandingFrame
from .reading import TRIANGLE, TriangleReader

SOUNDING_REACH: Final[int] = 2
JUDGED_FRAMES: Final[int] = 64
JUDGING_WIDTH: Final[int] = 1


class LevelFitter:
    """Finds the factor that moves the working level onto the triangle line a recording holds.

    The triangle plays one level, so a bass line fits it only where the working level brings the
    line there. The factor is found in three steps, on the recordings of the stems that may sound
    the triangle:

    1. Each frame its stem sounds through, ``SOUNDING_REACH`` frames on either side, is read at the
       first working level (:class:`TriangleReader`). A low note is read over a window several
       frames long, so a note a rest cuts short reads quieter than it plays.
    2. The readings give the level a triangle line stands at, where one stands and they agree
       (:class:`LevelReading`).
    3. The joint assignment chooses at most ``JUDGED_FRAMES`` of the standing frames, spread over
       them, at the first level and at the level read, each stem on its own channels
       (:class:`Judgment`). The sample bounds the judgment's cost however long the recording, and
       the judgment reads the choice alone, so every column is ``JUDGING_WIDTH`` wide. The level
       read holds where the triangle then plays the bass the frames were read on, and the frames
       cost less. A triangle note fitting a pulse's fundamental reads a level too, and at that
       level the choice gives the note back to the pulse, or the pulse falls short of what it then
       has to play.

    Attributes:
        channels: The run's channels.
        entries: The stems that may sound the triangle, in setup order.
        layouts: Each of those stems' layout, keyed by stem id.
        matcher: The matching machinery the frames are read and chosen with.
        config: The configuration the recordings are framed under.
        window: The analysis window the recordings are framed with.
    """

    def __init__(
        self,
        stems_config: StemsConfig,
        channels: Mapping[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
        config: Config,
        window: Window,
    ) -> None:
        self.channels = dict(channels)
        layouts = {entry.id: StemLayout.of(entry, self.channels) for entry in stems_config.entries}
        self.entries: List[StemEntry] = [entry for entry in stems_config.entries if layouts[entry.id].of_kind(TRIANGLE)]
        self.layouts: Dict[int, StemLayout] = {entry.id: layouts[entry.id] for entry in self.entries}
        self.matcher = matcher
        self.config = config
        self.window = window

    def factor(self, recordings: Mapping[int, np.ndarray], coefficient: float) -> Optional[float]:
        """The factor the working level moves by.

        Args:
            recordings: Every stem's loaded recording, keyed by stem id.
            coefficient: The working level the recordings are first matched at.

        Returns:
            The level the triangle line stands at, ``None`` where no stem may sound the triangle,
            no line stands, its readings disagree or the joint choice refuses the level.
        """
        if not self.entries:
            return None

        framed = self._framed(recordings, coefficient)
        reading = self.read(framed)
        level = reading.level
        if level is None:
            return None

        sample = reading.sample(JUDGED_FRAMES)
        first = self.judged(sample, framed)
        moved = self.judged(sample, self._framed(recordings, coefficient * level))
        return level if moved.holds_over(first) else None

    def read(self, frames: Mapping[int, FragmentedAudio]) -> LevelReading:
        """Reads every frame each stem that may sound the triangle sounds through, the stems in setup order.

        Args:
            frames: Each of those stems' frames, keyed by stem id.
        """
        catalogs = kind_catalogs(list(self.layouts.values()), self.channels, self.matcher.candidate_provider)
        readings: List[LevelReading] = []
        for entry in self.entries:
            reader = TriangleReader.of(self.layouts[entry.id], catalogs, self.matcher)
            readings.append(self._stem_reading(entry.id, frames[entry.id], reader))

        return LevelReading.pooled(readings)

    def judged(self, sample: Sequence[StandingFrame], frames: Mapping[int, FragmentedAudio]) -> Judgment:
        """How the joint assignment chooses the ``sample`` of ``frames``, each stem on its own channels.

        One assigner serves each stem through the sample, so it hands each frame's pulses over from
        the stem's choice in the frame sampled before it (``PulseHandover``).

        Args:
            sample: The standing frames to choose.
            frames: Each stem's frames, keyed by stem id.
        """
        assigners = {entry.id: self._lone_assigner(entry) for entry in self.entries}
        return Judgment.of([self._chosen(assigners[frame.stem_id], frame, frames[frame.stem_id]) for frame in sample])

    def _framed(self, recordings: Mapping[int, np.ndarray], coefficient: float) -> Dict[int, FragmentedAudio]:
        """Each stem's recording at the working level ``coefficient``, framed as the reconstructor frames it."""
        return {
            entry.id: FragmentedAudio.create(recordings[entry.id] / coefficient, self.config, self.window)
            for entry in self.entries
        }

    def _lone_assigner(self, entry: StemEntry) -> JointAssigner:
        """The joint assignment of ``entry``'s stem alone, on its own channels."""
        return JointAssigner(StemsConfig.single_entry(entry.settings), self.channels, self.matcher, JUDGING_WIDTH)

    @staticmethod
    def _chosen(assigner: JointAssigner, frame: StandingFrame, fragments: FragmentedAudio) -> ChosenFrame:
        """``frame`` of ``fragments`` as ``assigner`` chooses it, its one stem sounding the frame."""
        (layout,) = assigner.layouts
        assignment = assigner.assign({layout.stem_id: fragments[frame.index]})
        return ChosenFrame(choices=assignment.choices, note=frame.reading.note)

    @staticmethod
    def _stem_reading(stem_id: int, fragments: FragmentedAudio, reader: TriangleReader) -> LevelReading:
        """The reading of one stem's frames: every frame it sounds through read, the standing ones kept."""
        read = LevelFitter._sounded_through(fragments)
        standing: List[StandingFrame] = []
        for index in read:
            reading = reader.read(fragments[index])
            if reading is not None:
                standing.append(StandingFrame(stem_id=stem_id, index=index, reading=reading))

        return LevelReading(sampled=len(read), standing=tuple(standing))

    @staticmethod
    def _sounded_through(fragments: FragmentedAudio) -> List[int]:
        """The frames that sound (``frame_sounds``) with ``SOUNDING_REACH`` frames on either side sounding too."""
        sounding = np.array([frame_sounds(fragments[index]) for index in range(len(fragments))], dtype=bool)
        span = 2 * SOUNDING_REACH + 1
        if len(sounding) < span:
            return []

        through = sliding_window_view(sounding, span).all(axis=1)
        return [int(start) + SOUNDING_REACH for start in np.flatnonzero(through)]
