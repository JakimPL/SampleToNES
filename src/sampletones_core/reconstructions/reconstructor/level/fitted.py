from dataclasses import dataclass
from typing import Dict, Final, List, Mapping, Optional, Tuple

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

from sampletones_core.configs import Config
from sampletones_core.constants.algorithm import STEM_ACTIVITY_FLOOR
from sampletones_core.constants.enums import ChannelName, GeneratorClassName
from sampletones_core.fft import FragmentedAudio, Window
from sampletones_core.generators import GeneratorUnion
from sampletones_core.instructions import InstructionUnion, TriangleInstruction
from sampletones_core.reconstructions.reconstructor.matching import FrameMatcher
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.assigner import JointAssigner
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.catalog import KindCatalog
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.layout import StemLayout
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_shared.array import to_numpy

from .reading import TRIANGLE, FrameReading, TriangleReader

SOUNDING_REACH: Final[int] = 2
LEAST_STANDING_FRAMES: Final[int] = 4
LEAST_STANDING_SHARE: Final[float] = 0.5
MOST_SPREAD: Final[float] = 0.5
READING_WIDTH: Final[float] = 0.03
LOWER_QUARTILE: Final[float] = 25.0
UPPER_QUARTILE: Final[float] = 75.0
JUDGED_FRAMES: Final[int] = 64
JUDGING_WIDTH: Final[int] = 1
BASS_DISTANCE: Final[int] = 1
LEAST_CONFIRMED_SHARE: Final[float] = 0.6


@dataclass(frozen=True)
class StandingFrame:
    """A frame read with a triangle line holding its bass.

    Attributes:
        stem_id: The stem whose recording the frame is of.
        index: The frame's place in that recording.
        reading: Where its bass stands.
    """

    stem_id: int
    index: int
    reading: FrameReading


@dataclass(frozen=True)
class LevelReading:
    """What a recording's sampled frames say about the level its triangle line stands at.

    Attributes:
        sampled: How many frames were read.
        standing: The frames read whose bass a triangle line holds.
    """

    sampled: int
    standing: Tuple[StandingFrame, ...]

    @property
    def level(self) -> Optional[float]:
        """The level the frames agree the bass stands at, if they agree on one.

        A triangle line must hold the bass of at least ``LEAST_STANDING_SHARE`` of the frames read,
        and of ``LEAST_STANDING_FRAMES`` at least, and their readings must agree within ``MOST_SPREAD``
        of their median between the quartiles. A bass that rests between its notes or changes note
        within a frame's window reads quieter than it plays, and a pulse sharing its note lifts a
        frame's reading, while the frames that hold the line read alike. The level is the reading
        that the most others lie near, ``READING_WIDTH`` apart in log level counting as near.
        """
        if len(self.standing) < LEAST_STANDING_FRAMES or len(self.standing) < LEAST_STANDING_SHARE * self.sampled:
            return None

        levels = np.array([frame.reading.level for frame in self.standing])
        middle = float(np.median(levels))
        lower, upper = np.percentile(levels, [LOWER_QUARTILE, UPPER_QUARTILE])
        if middle <= 0.0 or upper - lower > MOST_SPREAD * middle:
            return None

        return _densest(levels)


@dataclass(frozen=True)
class Judgment:
    """How the joint assignment chooses a sample of a recording's frames at one working level.

    Attributes:
        cost: The median full cost of the frames as chosen.
        confirmed: The share of the frames whose triangle plays the bass they were read on.
    """

    cost: float
    confirmed: float


class LevelFitter:
    """Finds the working level at which a recording's triangle line plays on the triangle's one level.

    The frames of every stem that may sound the triangle are read at the level the input is first
    matched at (:class:`TriangleReader`). Where their readings agree on a level, the joint assignment
    chooses a sample of the frames at both levels. The new level holds where the triangle then plays
    the bass the frames were read on, within ``BASS_DISTANCE``, on at least ``LEAST_CONFIRMED_SHARE`` of
    them, and where the frames as chosen cost less than at the first level. A triangle note fitting
    a pulse's fundamental reads a level too, and at that level the choice gives the note back to the
    pulse, or the pulse falls short of what it then has to play.
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
        self.entries: List[StemEntry] = [
            entry for entry in stems_config.entries if StemLayout.of(entry, self.channels).of_kind(TRIANGLE)
        ]
        self.matcher = matcher
        self.config = config
        self.window = window

    def factor(self, recordings: Mapping[int, np.ndarray], coefficient: float) -> Optional[float]:
        """The factor the working level moves by, or ``None`` where the recordings hold no triangle line.

        Args:
            recordings: Every stem's loaded recording, keyed by stem id.
            coefficient: The working level the recordings are first matched at.
        """
        if not self.entries:
            return None

        reading = self.read({entry.id: self._frames(recordings[entry.id], coefficient) for entry in self.entries})
        level = reading.level
        if level is None:
            return None

        sample = _spread_sample(list(reading.standing), JUDGED_FRAMES)
        first = self.judged(
            sample, {entry.id: self._frames(recordings[entry.id], coefficient) for entry in self.entries}
        )
        moved = self.judged(
            sample, {entry.id: self._frames(recordings[entry.id], coefficient * level) for entry in self.entries}
        )
        holds = moved.confirmed >= LEAST_CONFIRMED_SHARE and moved.cost < first.cost
        return level if holds else None

    def read(self, frames: Mapping[int, FragmentedAudio]) -> LevelReading:
        """Reads every frame each stem that may sound the triangle sounds through.

        A frame is read where its stem sounds for ``SOUNDING_REACH`` frames on either side of it. A low
        note is read over a window several frames long, so a note a rest cuts short reads quieter than
        it plays.
        """
        catalogs = self._catalogs()
        sampled = 0
        standing: List[StandingFrame] = []
        for entry in self.entries:
            reader = TriangleReader.of(StemLayout.of(entry, self.channels), catalogs, self.matcher)
            fragments = frames[entry.id]
            for index in _sounded_through(fragments):
                sampled += 1
                reading = reader.read(fragments[index])
                if reading is not None:
                    standing.append(StandingFrame(stem_id=entry.id, index=index, reading=reading))

        return LevelReading(sampled=sampled, standing=tuple(standing))

    def judged(self, sample: List[StandingFrame], frames: Mapping[int, FragmentedAudio]) -> Judgment:
        """How the joint assignment chooses the ``sample`` of ``frames``, each stem on its own channels."""
        assigners = {
            entry.id: JointAssigner(
                StemsConfig.single_entry(entry.settings), self.channels, self.matcher, JUDGING_WIDTH
            )
            for entry in self.entries
        }
        costs: List[float] = []
        confirmed = 0
        for frame in sample:
            choices = assigners[frame.stem_id].assign({0: frames[frame.stem_id][frame.index]}).choices
            if choices:
                costs.append(min(choice.cost for choice in choices))
            confirmed += any(
                self._plays_bass(choice.channel_name, choice.instruction, frame.reading.note) for choice in choices
            )

        return Judgment(
            cost=float(np.median(costs)) if costs else float("inf"),
            confirmed=confirmed / len(sample) if sample else 0.0,
        )

    def _plays_bass(self, channel_name: ChannelName, instruction: InstructionUnion, note: int) -> bool:
        """Whether a channel plays ``note`` on the triangle, within ``BASS_DISTANCE``."""
        return (
            self.channels[channel_name].class_name() == TRIANGLE
            and isinstance(instruction, TriangleInstruction)
            and instruction.on
            and abs(instruction.pitch - note) <= BASS_DISTANCE
        )

    def _catalogs(self) -> Dict[GeneratorClassName, KindCatalog]:
        catalogs: Dict[GeneratorClassName, KindCatalog] = {}
        for entry in self.entries:
            for slot in StemLayout.of(entry, self.channels).slots:
                if slot.kind not in catalogs:
                    catalogs[slot.kind] = KindCatalog.build(
                        self.matcher.candidate_provider, self.channels[slot.channel_name]
                    )

        return catalogs

    def _frames(self, recording: np.ndarray, coefficient: float) -> FragmentedAudio:
        return FragmentedAudio.create(recording / coefficient, self.config, self.window)


def _sounded_through(fragments: FragmentedAudio) -> List[int]:
    """The frames that, with ``SOUNDING_REACH`` frames on either side, are loud enough for a channel to render."""
    sounding = np.array(
        [
            float(np.max(np.abs(to_numpy(fragments[index].audio)), initial=0.0)) >= STEM_ACTIVITY_FLOOR
            for index in range(len(fragments))
        ],
        dtype=bool,
    )
    span = 2 * SOUNDING_REACH + 1
    if len(sounding) < span:
        return []

    through = sliding_window_view(sounding, span).all(axis=1)
    return [int(start) + SOUNDING_REACH for start in np.flatnonzero(through)]


def _densest(levels: np.ndarray) -> float:
    """The level of ``levels`` the most others lie near, each weighed by a Gaussian ``READING_WIDTH`` wide in log level."""
    logs = np.log(levels)
    nearness = np.exp(-0.5 * ((logs[:, None] - logs[None, :]) / READING_WIDTH) ** 2).sum(axis=1)
    return float(levels[int(np.argmax(nearness))])


def _spread_sample(frames: List[StandingFrame], count: int) -> List[StandingFrame]:
    """At most ``count`` of ``frames``, spread evenly over them."""
    if len(frames) <= count:
        return frames

    return [frames[int(position)] for position in np.linspace(0, len(frames) - 1, count)]
