import itertools
from dataclasses import dataclass
from typing import Dict, Final, FrozenSet, Mapping, Optional, Sequence, Set, Tuple

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

TONAL_CHANNELS: Final[Tuple[ChannelName, ...]] = tuple(ordered_channels(TONE_CHANNELS))

NoteOptions = FrozenSet[Optional[Note]]


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

    def add(
        self,
        target: FrozenSet[Note],
        options: Mapping[ChannelName, NoteOptions],
        heads: FrozenSet[Note],
        decoded: FrozenSet[Note],
    ) -> None:
        """Counts one sounding frame by where its written notes were lost, if they were."""
        self.sounding += 1
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
    of written notes no column offers on their channel kind (``unreached``).
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
            )

        return tally.judgment()


def formable(target: FrozenSet[Note], options: Mapping[ChannelName, NoteOptions]) -> bool:
    """Whether one option per channel sounds exactly ``target``, a channel's silence one of its options."""
    choices: Sequence[NoteOptions] = list(options.values())
    for chosen in itertools.product(*choices):
        if frozenset(note for note in chosen if note is not None) == target:
            return True

    return False


def _column(trace: SearchTrace, channel: ChannelName, frame: int) -> Tuple[Frame, ...]:
    """The candidates a channel's column offers at ``frame``; a channel the conversion leaves out offers silence."""
    columns = trace.columns.get(channel, ())
    return columns[frame] if frame < len(columns) else (None,)


def _options(reader: NoteReader, channel: ChannelName, trace: SearchTrace, frame: int) -> NoteOptions:
    return frozenset(reader.note(channel, candidate) for candidate in _column(trace, channel, frame))


def _heads(reader: NoteReader, trace: SearchTrace, frame: int) -> FrozenSet[Note]:
    """The notes the columns' heads sound together, which is what the assignment picked."""
    return reader.notes({channel: _column(trace, channel, frame)[0] for channel in TONAL_CHANNELS})
