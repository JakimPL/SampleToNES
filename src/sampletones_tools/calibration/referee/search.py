import itertools
from dataclasses import dataclass, field
from typing import Dict, Final, FrozenSet, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions import Reconstruction
from sampletones_tools.calibration.corpus.truth import Truth
from sampletones_tools.calibration.trace import PoolTrace, SearchTrace

from .frames import Frame, channel_streams, common_length, sounds
from .notes import TONAL_CHANNELS, Note, NoteReader, pitches_of
from .protocol import Judgment

SEARCH_REFEREE: Final[str] = "search"
UNREACHED: Final[str] = "unreached"
COLUMNS: Final[str] = "columns"
ASSIGNMENT: Final[str] = "assignment"
DECODER: Final[str] = "decoder"
GAINS: Final[str] = "gains"
MISPLACED: Final[str] = "misplaced"
POOLED: Final[str] = "pooled"
AT_CHANGE: Final[str] = "at-change"
NEXT_TO_CHANGE: Final[str] = "next-to-change"
AWAY_FROM_CHANGE: Final[str] = "away-from-change"
STAGES: Final[Tuple[str, ...]] = (COLUMNS, ASSIGNMENT, DECODER)
CHANGE_READINGS: Final[Tuple[str, ...]] = (AT_CHANGE, NEXT_TO_CHANGE, AWAY_FROM_CHANGE)
AT_CHANGE_DISTANCE: Final[int] = 0
NEXT_TO_CHANGE_DISTANCE: Final[int] = 1

NoteOptions = FrozenSet[Optional[Note]]
PoolNotes = FrozenSet[FrozenSet[Note]]
Streams = Dict[ChannelName, Tuple[Frame, ...]]


@dataclass(frozen=True)
class SearchFrame:
    """What a search held of one frame the writing sounds, stage by stage, read as the notes each sounds.

    The search narrows a frame in stages: the columns offer candidates per channel, the assignment picks
    one per channel (each column's head), and the decoder settles the frame. The written notes are lost
    at the first stage that can no longer sound them.

    Attributes:
        target: The notes the writing sounds.
        options: The notes each tonal channel's column offers, ``None`` for a silent candidate.
        heads: The notes the columns' heads sound together, which is what the assignment picked.
        decoded: The notes the decoded frame sounds.
        pools: The note sets each stem's pool offers, ``None`` where the search pooled no combinations.
        change_distance: How many frames the frame stands from the nearest frame at a written note change.
    """

    target: FrozenSet[Note]
    options: Mapping[ChannelName, NoteOptions]
    heads: FrozenSet[Note]
    decoded: FrozenSet[Note]
    pools: Optional[Sequence[PoolNotes]]
    change_distance: int

    @property
    def right(self) -> bool:
        """Whether the decoded frame sounds the written notes, each on its written channel kind."""
        return self.decoded == self.target

    @property
    def lost_at(self) -> Optional[str]:
        """The first stage that could no longer sound the written notes, ``None`` for a right frame.

        The columns lose them where no choice of one candidate per channel forms them; the assignment,
        where the columns could and the picks do not; the decoder, where the picks had them.
        """
        if self.right:
            return None

        if not formable(self.target, self.options):
            return COLUMNS

        if self.heads != self.target:
            return ASSIGNMENT

        return DECODER

    @property
    def gained(self) -> bool:
        """Whether the decoder put right a frame the picks had wrong."""
        return self.right and self.heads != self.target

    @property
    def misplaced(self) -> bool:
        """Whether a wrong frame sounds the written pitches as a set, on other channel kinds."""
        return not self.right and pitches_of(self.decoded) == pitches_of(self.target)

    @property
    def unreached(self) -> int:
        """How many written notes no column offers on their channel kind."""
        offered: Set[Optional[Note]] = set().union(*self.options.values())
        return sum(note not in offered for note in self.target)

    @property
    def pooled(self) -> Optional[bool]:
        """Whether the stems' pools can sound the written notes, ``None`` where the search pooled none."""
        if self.pools is None:
            return None

        return poolable(self.target, self.pools)

    @property
    def change_reading(self) -> str:
        """The change reading the frame counts in: at a written note change, next to one, or further."""
        if self.change_distance == AT_CHANGE_DISTANCE:
            return AT_CHANGE

        if self.change_distance == NEXT_TO_CHANGE_DISTANCE:
            return NEXT_TO_CHANGE

        return AWAY_FROM_CHANGE


@dataclass
class SearchTally:
    """The sounding frames a search reading counts, sorted by the stage that lost the written notes."""

    sounding: int = 0
    right: int = 0
    lost: Dict[str, int] = field(default_factory=lambda: dict.fromkeys(STAGES, 0))
    gains: int = 0
    misplaced: int = 0
    written_notes: int = 0
    unreached_notes: int = 0
    pool_frames: int = 0
    pooled: int = 0
    by_change: Dict[str, int] = field(default_factory=lambda: dict.fromkeys(CHANGE_READINGS, 0))
    wrong_by_change: Dict[str, int] = field(default_factory=lambda: dict.fromkeys(CHANGE_READINGS, 0))

    def add(self, frame: SearchFrame) -> None:
        """Counts one sounding frame by where its written notes were lost, if they were."""
        self.sounding += 1
        self._count_change(frame)
        self._count_pool(frame)
        self.written_notes += len(frame.target)
        self.unreached_notes += frame.unreached
        stage = frame.lost_at
        if stage is None:
            self.right += 1
            self.gains += frame.gained
            return

        self.misplaced += frame.misplaced
        self.lost[stage] += 1

    def judgment(self) -> Optional[Judgment]:
        """The share of sounding frames decoded with other notes than written, and where they were lost.

        Returns:
            Optional[Judgment]: The judgment, or ``None`` where the writing sounds no frame.
        """
        if not self.sounding:
            return None

        components: Dict[str, float] = {stage: self.lost[stage] / self.sounding for stage in STAGES}
        components[GAINS] = self.gains / self.sounding
        components[MISPLACED] = self.misplaced / self.sounding
        if self.written_notes:
            components[UNREACHED] = self.unreached_notes / self.written_notes

        if self.pool_frames:
            components[POOLED] = self.pooled / self.pool_frames

        for reading in CHANGE_READINGS:
            if self.by_change[reading]:
                components[reading] = self.wrong_by_change[reading] / self.by_change[reading]

        return Judgment(score=1.0 - self.right / self.sounding, components=components)

    def _count_change(self, frame: SearchFrame) -> None:
        reading = frame.change_reading
        self.by_change[reading] += 1
        self.wrong_by_change[reading] += not frame.right

    def _count_pool(self, frame: SearchFrame) -> None:
        pooled = frame.pooled
        if pooled is not None:
            self.pool_frames += 1
            self.pooled += pooled


@dataclass(frozen=True)
class TraceNotes:
    """A search trace read as notes: what each frame's columns, picks and pools offered.

    A channel the conversion leaves out offers silence alone.

    Attributes:
        reader: Reads the notes the candidates sound.
        trace: What the search offered and chose, frame by frame.
    """

    reader: NoteReader
    trace: SearchTrace

    def options(self, frame: int) -> Dict[ChannelName, NoteOptions]:
        """The notes each tonal channel's column offers at ``frame``, ``None`` for a silent candidate."""
        return {
            channel: frozenset(self.reader.note(channel, candidate) for candidate in self._column(channel, frame))
            for channel in TONAL_CHANNELS
        }

    def heads(self, frame: int) -> FrozenSet[Note]:
        """The notes the columns' heads sound together at ``frame``, which is what the assignment picked."""
        return self.reader.notes({channel: self._column(channel, frame)[0] for channel in TONAL_CHANNELS})

    def pools(self, frame: int) -> Optional[List[PoolNotes]]:
        """The note sets each stem's pool offers at ``frame``, or ``None`` where the trace holds no pools.

        A pool shorter than the frame offers nothing there and is left out.
        """
        if not self.trace.pools:
            return None

        return [self._pool_notes(pool, frame) for pool in self.trace.pools.values() if frame < len(pool.frames)]

    def _pool_notes(self, pool: PoolTrace, frame: int) -> PoolNotes:
        """The note sets the combinations of ``pool`` sound at ``frame``."""
        return frozenset(
            self.reader.notes(dict(zip(pool.channel_names, combination))) for combination in pool.frames[frame]
        )

    def _column(self, channel: ChannelName, frame: int) -> Tuple[Frame, ...]:
        """The candidates a channel's column offers at ``frame``, the assignment's pick first."""
        columns = self.trace.columns.get(channel, ())
        return columns[frame] if frame < len(columns) else (None,)


class SearchReferee:
    """Reads where a conversion's search loses the notes a sound written as NES frames plays.

    A frame counts where the writing sounds any channel, and it is right where the decoded frame sounds
    the written notes on the written channel kinds: the two pulses one kind, a unison one note, the
    noise left to the transcription. A wrong frame is lost at the first stage that could no longer
    reach the written notes (see ``SearchFrame.lost_at``).

    The score is the share of counted frames decoded wrong, zero being closest. Its readings, each a
    share where zero is closest unless named otherwise:

    - ``columns``, ``assignment``, ``decoder``: the counted frames lost at each stage;
    - ``gains``: the counted frames the decoder put right after the picks had them wrong, higher being
      better for the decoder;
    - ``misplaced``: the counted frames decoded wrong whose decoded pitches are the written ones, on
      other channel kinds;
    - ``unreached``: the written notes no column offers on their channel kind;
    - ``pooled``: where the search pooled whole combinations, the counted frames whose pools can sound
      the written notes, one combination per stem, higher being closer;
    - ``at-change``, ``next-to-change``, ``away-from-change``: the share decoded wrong among the frames
      at a written note change, where a tonal channel starts, stops or moves between the frame and the
      one beside it, among those one frame from one, and among those further. A frame's analysis window
      reads its neighbors, so these readings say where the window's reach costs notes.
    """

    @property
    def name(self) -> str:
        return SEARCH_REFEREE

    def judge(self, truth: Truth, trace: SearchTrace, reconstruction: Reconstruction) -> Optional[Judgment]:
        """Where ``trace`` lost the notes ``truth`` writes.

        Returns:
            Optional[Judgment]: The judgment, or ``None`` for a sound written as no frames.
        """
        if not truth.instructions:
            return None

        reader = NoteReader(reconstruction.config)
        length = common_length(*truth.instructions.values(), *trace.decoded.values())
        written = channel_streams(truth.instructions, length)
        decoded = channel_streams(trace.decoded, length)
        distances = change_distances([_channel_notes(reader, written, frame) for frame in range(length)])
        offered = TraceNotes(reader=reader, trace=trace)
        tally = SearchTally()
        for frame in range(length):
            if not any(sounds(stream[frame]) for stream in written.values()):
                continue

            tally.add(
                SearchFrame(
                    target=reader.notes(_tonal_frames(written, frame)),
                    options=offered.options(frame),
                    heads=offered.heads(frame),
                    decoded=reader.notes(_tonal_frames(decoded, frame)),
                    pools=offered.pools(frame),
                    change_distance=distances[frame],
                )
            )

        return tally.judgment()


def change_distances(notes: Sequence[Tuple[Optional[Note], ...]]) -> List[int]:
    """How far each frame stands from the nearest frame at a note change, in frames.

    A note change lies between two frames whose notes differ on some channel, and both frames stand
    at it. A writing that never changes stands as far from a change as it is long.

    Args:
        notes: Each frame's note on every channel, ``None`` where the channel is silent.

    Returns:
        One distance per frame.
    """
    return _distances_to(_frames_at_change(notes))


def formable(target: FrozenSet[Note], options: Mapping[ChannelName, NoteOptions]) -> bool:
    """Whether one option per channel sounds exactly ``target``, a channel's silence one of its options."""
    return any(_sounded(chosen) == target for chosen in itertools.product(*options.values()))


def poolable(target: FrozenSet[Note], pools: Sequence[PoolNotes]) -> bool:
    """Whether one combination from every stem's pool sounds exactly ``target`` together.

    A stem's combination joins a match only where it sounds part of ``target``, so each pool is
    narrowed to those before the stems' choices are crossed.
    """
    within = [[notes for notes in pool if notes <= target] for pool in pools]
    return any(frozenset().union(*chosen) == target for chosen in itertools.product(*within))


def _frames_at_change(notes: Sequence[Tuple[Optional[Note], ...]]) -> List[bool]:
    """Which frames stand at a note change: both frames on either side of one."""
    at_change = [False] * len(notes)
    for frame in range(1, len(notes)):
        if notes[frame] != notes[frame - 1]:
            at_change[frame - 1] = at_change[frame] = True

    return at_change


def _distances_to(marked: Sequence[bool]) -> List[int]:
    """How far each frame stands from the nearest marked frame, as many frames as there are where none is marked.

    The distance is carried forward from each marked frame, then back, so each frame keeps the nearer.
    """
    length = len(marked)
    distances = [length] * length
    for frame in range(length):
        if marked[frame]:
            distances[frame] = 0
        elif frame:
            distances[frame] = min(distances[frame - 1] + 1, length)

    for frame in reversed(range(length - 1)):
        distances[frame] = min(distances[frame], distances[frame + 1] + 1)

    return distances


def _sounded(chosen: Iterable[Optional[Note]]) -> FrozenSet[Note]:
    """The notes a choice of one option per channel sounds together."""
    return frozenset(note for note in chosen if note is not None)


def _tonal_frames(streams: Streams, frame: int) -> Dict[ChannelName, Frame]:
    """Every tonal channel's frame ``frame``."""
    return {channel: streams[channel][frame] for channel in TONAL_CHANNELS}


def _channel_notes(reader: NoteReader, written: Streams, frame: int) -> Tuple[Optional[Note], ...]:
    """The note each tonal channel sounds in frame ``frame``, ``None`` where it is silent."""
    return tuple(reader.note(channel, instruction) for channel, instruction in _tonal_frames(written, frame).items())
