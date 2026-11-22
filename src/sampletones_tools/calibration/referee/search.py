import itertools
from dataclasses import dataclass, field
from typing import Dict, Final, FrozenSet, List, Mapping, Optional, Sequence, Set, Tuple

from sampletones_core.constants.enums import TONE_CHANNELS, ChannelName, ordered_channels
from sampletones_core.reconstructions import Reconstruction
from sampletones_tools.calibration.corpus.truth import Truth
from sampletones_tools.calibration.trace import SearchTrace

from .frames import Frame, channel_streams, common_length, sounds
from .notes import Note, NoteReader, pitches_of
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
CHANGE_READINGS: Final[Tuple[str, ...]] = (AT_CHANGE, NEXT_TO_CHANGE, AWAY_FROM_CHANGE)

TONAL_CHANNELS: Final[Tuple[ChannelName, ...]] = tuple(ordered_channels(TONE_CHANNELS))

NoteOptions = FrozenSet[Optional[Note]]
PoolNotes = FrozenSet[FrozenSet[Note]]


@dataclass
class SearchTally:
    """The sounding frames a search reading counts, sorted by the stage that lost the written notes."""

    sounding: int = 0
    right: int = 0
    columns: int = 0
    assignment: int = 0
    decoder: int = 0
    gains: int = 0
    misplaced: int = 0
    written_notes: int = 0
    unreached_notes: int = 0
    pool_frames: int = 0
    pooled: int = 0
    by_change: Dict[str, int] = field(default_factory=lambda: dict.fromkeys(CHANGE_READINGS, 0))
    wrong_by_change: Dict[str, int] = field(default_factory=lambda: dict.fromkeys(CHANGE_READINGS, 0))

    def add(
        self,
        target: FrozenSet[Note],
        options: Mapping[ChannelName, NoteOptions],
        heads: FrozenSet[Note],
        decoded: FrozenSet[Note],
        pools: Optional[Sequence[PoolNotes]],
        change_distance: int,
    ) -> None:
        """Counts one sounding frame by where its written notes were lost, if they were.

        ``pools`` holds the note sets each stem's pool offers the frame, or ``None`` where the search
        pooled no combinations. ``change_distance`` is how many frames the frame stands from the
        nearest frame at a written note change.
        """
        self.sounding += 1
        near = _change_reading(change_distance)
        self.by_change[near] += 1
        self.wrong_by_change[near] += decoded != target
        if pools is not None:
            self.pool_frames += 1
            self.pooled += poolable(target, pools)
        offered: Set[Optional[Note]] = set().union(*options.values())
        self.written_notes += len(target)
        self.unreached_notes += sum(note not in offered for note in target)
        if decoded == target:
            self.right += 1
            self.gains += heads != target
            return

        self.misplaced += pitches_of(decoded) == pitches_of(target)
        if not formable(target, options):
            self.columns += 1
        elif heads != target:
            self.assignment += 1
        else:
            self.decoder += 1

    def judgment(self) -> Optional[Judgment]:
        """The share of sounding frames decoded with other notes than written, and where they were lost.

        Returns:
            Optional[Judgment]: The judgment, or ``None`` where the writing sounds no frame.
        """
        if not self.sounding:
            return None

        components: Dict[str, float] = {
            COLUMNS: self.columns / self.sounding,
            ASSIGNMENT: self.assignment / self.sounding,
            DECODER: self.decoder / self.sounding,
            GAINS: self.gains / self.sounding,
            MISPLACED: self.misplaced / self.sounding,
        }
        if self.written_notes:
            components[UNREACHED] = self.unreached_notes / self.written_notes
        if self.pool_frames:
            components[POOLED] = self.pooled / self.pool_frames
        for reading in CHANGE_READINGS:
            if self.by_change[reading]:
                components[reading] = self.wrong_by_change[reading] / self.by_change[reading]

        return Judgment(score=1.0 - self.right / self.sounding, components=components)


class SearchReferee:
    """Reads where a conversion's search loses the notes a sound written as NES frames plays.

    A frame counts where the writing sounds any channel, and it is right where the decoded frame sounds
    the written notes on the written channel kinds: the two pulses one kind, a unison one note, the
    noise left to the transcription. A wrong frame is lost at the first stage that could no longer
    reach the written notes: the columns, where no choice of one candidate per channel forms them; the
    assignment, where the columns could and the picks heading them do not; or the decoder, where the
    picks had them and the decoded frame moved away.

    The score is the share of counted frames decoded wrong. The readings behind it are the share lost
    at each stage, the share the decoder put right after the picks had it wrong (``gains``), the share
    whose decoded pitches are the written ones on another channel kind (``misplaced``), and the share
    of written notes no column offers on their channel kind (``unreached``). Where the search pooled
    whole combinations, ``pooled`` is the share of counted frames whose pools can sound the written
    notes, one combination per stem. A frame's analysis window reads its neighbors, so the share
    decoded wrong is also read by how near the frame stands to a written note change: at one, where a
    tonal channel starts, stops or moves between the frame and the one beside it (``at-change``),
    one frame further (``next-to-change``), or further still (``away-from-change``).
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
        distances = change_distances(
            [
                tuple(reader.note(channel, written[channel][frame]) for channel in TONAL_CHANNELS)
                for frame in range(length)
            ]
        )
        tally = SearchTally()
        for frame in range(length):
            if not any(sounds(stream[frame]) for stream in written.values()):
                continue

            options = {channel: _options(reader, channel, trace, frame) for channel in TONAL_CHANNELS}
            tally.add(
                reader.notes({channel: written[channel][frame] for channel in TONAL_CHANNELS}),
                options,
                _heads(reader, trace, frame),
                reader.notes({channel: decoded[channel][frame] for channel in TONAL_CHANNELS}),
                _pool_notes(reader, trace, frame),
                distances[frame],
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
    length = len(notes)
    at_change = [False] * length
    for frame in range(1, length):
        if notes[frame] != notes[frame - 1]:
            at_change[frame - 1] = at_change[frame] = True

    distances = [length] * length
    for frame in range(length):
        if at_change[frame]:
            distances[frame] = 0
        elif frame:
            distances[frame] = min(distances[frame - 1] + 1, length)
    for frame in reversed(range(length - 1)):
        distances[frame] = min(distances[frame], distances[frame + 1] + 1)

    return distances


def _change_reading(distance: int) -> str:
    """The change reading a frame ``distance`` frames from a note change counts in."""
    if distance == 0:
        return AT_CHANGE
    if distance == 1:
        return NEXT_TO_CHANGE
    return AWAY_FROM_CHANGE


def formable(target: FrozenSet[Note], options: Mapping[ChannelName, NoteOptions]) -> bool:
    """Whether one option per channel sounds exactly ``target``, a channel's silence one of its options."""
    choices: Sequence[NoteOptions] = list(options.values())
    for chosen in itertools.product(*choices):
        if frozenset(note for note in chosen if note is not None) == target:
            return True

    return False


def poolable(target: FrozenSet[Note], pools: Sequence[PoolNotes]) -> bool:
    """Whether one combination from every stem's pool sounds exactly ``target`` together.

    A stem's combination joins a match only where it sounds part of ``target``, so each pool is
    narrowed to those before the stems' choices are crossed.
    """
    within = [[notes for notes in pool if notes <= target] for pool in pools]
    for chosen in itertools.product(*within):
        if frozenset().union(*chosen) == target:
            return True

    return False


def _pool_notes(reader: NoteReader, trace: SearchTrace, frame: int) -> Optional[List[PoolNotes]]:
    """The note sets each stem's pool offers at ``frame``, or ``None`` where the trace holds no pools."""
    if not trace.pools:
        return None

    return [
        frozenset(reader.notes(dict(zip(pool.channel_names, combination))) for combination in pool.frames[frame])
        for pool in trace.pools.values()
        if frame < len(pool.frames)
    ]


def _column(trace: SearchTrace, channel: ChannelName, frame: int) -> Tuple[Frame, ...]:
    """The candidates a channel's column offers at ``frame``; a channel the conversion leaves out offers silence."""
    columns = trace.columns.get(channel, ())
    return columns[frame] if frame < len(columns) else (None,)


def _options(reader: NoteReader, channel: ChannelName, trace: SearchTrace, frame: int) -> NoteOptions:
    return frozenset(reader.note(channel, candidate) for candidate in _column(trace, channel, frame))


def _heads(reader: NoteReader, trace: SearchTrace, frame: int) -> FrozenSet[Note]:
    """The notes the columns' heads sound together, which is what the assignment picked."""
    return reader.notes({channel: _column(trace, channel, frame)[0] for channel in TONAL_CHANNELS})
