from dataclasses import dataclass, field
from typing import Dict, Final, List, Optional, Self, Sequence, Set, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import NoiseInstruction, PulseInstruction, TriangleInstruction
from sampletones_core.reconstructions import Reconstruction
from sampletones_tools.calibration.corpus.truth import Truth

from .frames import Frame, channel_streams, common_length, sounds
from .notes import Note, NoteReader, timbre_of
from .protocol import Judgment
from .scale import effective_scale

TRANSCRIPTION_REFEREE: Final[str] = "transcription"
MISSED: Final[str] = "missed"
SPURIOUS: Final[str] = "spurious"
MISPLACED: Final[str] = "misplaced"
NOTE: Final[str] = "note"
VOLUME: Final[str] = "volume"
DUTY: Final[str] = "duty"
PERIOD: Final[str] = "period"
MODE: Final[str] = "mode"

PULSES: Final[Tuple[ChannelName, ChannelName]] = (ChannelName.PULSE1, ChannelName.PULSE2)
SOLE_CHANNELS: Final[Tuple[ChannelName, ...]] = (ChannelName.TRIANGLE, ChannelName.NOISE)

ChannelPairing = List[Tuple[ChannelName, ChannelName]]


@dataclass(frozen=True)
class FieldComparison:
    """Holds a played frame's fields against a written frame's, at the level the sound itself holds.

    A conversion matches its sound at a working level, so a played volume times ``scale`` is the volume
    the sound holds. Read there, a conversion at another working level is charged for it once, by the
    balance's ``scale`` reading. The duty is read as the timbre it sounds.

    Attributes:
        volume_tolerance: The volume steps a played frame may stand off the written one by and agree.
        scale: The working-level scale the conversion matched its sound at.
    """

    volume_tolerance: int
    scale: float

    def agreements(self, written: Frame, played: Frame) -> Dict[str, bool]:
        """Whether each field the channel takes agrees between two sounding frames of it.

        Raises:
            TypeError: If the two frames belong to different channels.
        """
        match written, played:
            case PulseInstruction(), PulseInstruction():
                return {
                    NOTE: written.pitch == played.pitch,
                    DUTY: timbre_of(written.duty_cycle) == timbre_of(played.duty_cycle),
                    VOLUME: self._volume_agrees(written.volume, played.volume),
                }
            case TriangleInstruction(), TriangleInstruction():
                return {NOTE: written.pitch == played.pitch}
            case NoiseInstruction(), NoiseInstruction():
                return {
                    PERIOD: written.period == played.period,
                    MODE: written.short == played.short,
                    VOLUME: self._volume_agrees(written.volume, played.volume),
                }
            case _:
                raise TypeError(f"Frames of different channels compared: {written!r} and {played!r}")

    def disagreements(self, written: Frame, played: Frame) -> int:
        """How many fields disagree between two frames of a channel, a frame sounding on one side alone counting one."""
        if sounds(written) and sounds(played):
            return sum(not agrees for agrees in self.agreements(written, played).values())

        return int(sounds(written) != sounds(played))

    def _volume_agrees(self, written: int, played: int) -> bool:
        return abs(written - played * self.scale) <= self.volume_tolerance


@dataclass(frozen=True)
class FramePair:
    """One channel-frame as written and as played, with the notes each side sounds on a tonal channel.

    Attributes:
        written: The written frame.
        played: The played frame.
        written_note: The note the written frame sounds, ``None`` for silence or the noise.
        played_note: The note the played frame sounds, ``None`` for silence or the noise.
    """

    written: Frame
    played: Frame
    written_note: Optional[Note]
    played_note: Optional[Note]

    @property
    def written_sounds(self) -> bool:
        """Whether the writing sounds this channel-frame."""
        return sounds(self.written)

    @property
    def played_sounds(self) -> bool:
        """Whether the conversion sounds this channel-frame."""
        return sounds(self.played)

    @property
    def missing_note(self) -> Optional[Note]:
        """The written note this channel leaves off, ``None`` where it plays it or the writing sounds none."""
        if self.written_note is not None and self.played_note != self.written_note:
            return self.written_note

        return None

    @property
    def missing(self) -> bool:
        """Whether the written note is absent from what this channel plays."""
        return self.missing_note is not None

    @property
    def added(self) -> bool:
        """Whether this channel plays a note the writing leaves off it."""
        return self.played_note is not None and self.written_note != self.played_note

    def adds_on_another_kind(self, note: Note) -> bool:
        """Whether this channel adds a note at the pitch of ``note`` on a channel kind other than ``note``'s."""
        return (
            self.added
            and self.played_note is not None
            and self.played_note.semitone == note.semitone
            and self.played_note.kind != note.kind
        )


@dataclass(frozen=True)
class Transcript:
    """A sound's written frames beside the frames its conversion plays, read channel-frame by channel-frame.

    The two pulses sound one mix whichever of them carries which line, so each frame reads them across
    straight or crossed, whichever pairing disagrees on fewer fields, straight where both disagree
    equally. How often the conversion swaps its pulses is the stability's reading. The triangle and
    the noise each read against themselves.

    Attributes:
        written: Every channel's written frames.
        played: Every channel's played frames, as many as written.
        reader: Reads the notes the frames sound.
        comparison: Holds the played fields against the written ones.
    """

    written: Dict[ChannelName, Tuple[Frame, ...]]
    played: Dict[ChannelName, Tuple[Frame, ...]]
    reader: NoteReader
    comparison: FieldComparison

    def pairs(self, frame: int) -> List[FramePair]:
        """Every channel-frame of ``frame``: the pulses as paired, then the triangle and the noise."""
        channels = self._pulse_pairing(frame) + [(channel, channel) for channel in SOLE_CHANNELS]
        return [self._pair(frame, written_channel, played_channel) for written_channel, played_channel in channels]

    def _pulse_pairing(self, frame: int) -> ChannelPairing:
        """The written and played pulse each pulse line is read across in ``frame``, straight or crossed."""
        first, second = PULSES
        straight = [(first, first), (second, second)]
        crossed = [(first, second), (second, first)]
        if self._disagreements(crossed, frame) < self._disagreements(straight, frame):
            return crossed

        return straight

    def _disagreements(self, pairing: ChannelPairing, frame: int) -> int:
        """How many fields disagree in ``frame`` across the channels ``pairing`` reads together."""
        return sum(
            self.comparison.disagreements(self.written[written_channel][frame], self.played[played_channel][frame])
            for written_channel, played_channel in pairing
        )

    def _pair(self, frame: int, written_channel: ChannelName, played_channel: ChannelName) -> FramePair:
        written = self.written[written_channel][frame]
        played = self.played[played_channel][frame]
        return FramePair(
            written=written,
            played=played,
            written_note=self.reader.note(written_channel, written),
            played_note=self.reader.note(played_channel, played),
        )


@dataclass(frozen=True)
class Misplacements:
    """The written notes of one frame played at their pitch on another channel kind, such as a bass on a pulse.

    Each written note a channel leaves off is matched with the first other channel, not matched yet,
    that adds a note at its pitch on another channel kind.

    Attributes:
        missing: The pairs whose written note is played elsewhere.
        added: The pairs playing a written note of another channel kind.
    """

    missing: Set[int]
    added: Set[int]

    @classmethod
    def of(cls, pairs: Sequence[FramePair]) -> Self:
        """Pairs each missing written note with one added note of its pitch on another channel kind."""
        missing: Set[int] = set()
        added: Set[int] = set()
        for index, pair in enumerate(pairs):
            note = pair.missing_note
            if note is None:
                continue

            player = cls._player(index, note, pairs, added)
            if player is not None:
                missing.add(index)
                added.add(player)

        return cls(missing=missing, added=added)

    def passes_through(self, index: int) -> bool:
        """Whether a misplaced note passes through pair ``index``, left off or played there."""
        return index in self.missing or index in self.added

    @staticmethod
    def _player(index: int, note: Note, pairs: Sequence[FramePair], taken: Set[int]) -> Optional[int]:
        """The first pair besides ``index``, not taken yet, adding ``note``'s pitch on another channel kind."""
        for other, candidate in enumerate(pairs):
            if other != index and other not in taken and candidate.adds_on_another_kind(note):
                return other

        return None


@dataclass
class Tally:
    """The channel-frames a transcription counts, and those that miss in each way.

    A channel-frame counts where the writing or the conversion sounds it, and counts one error where it
    is played otherwise than written. A misplaced note is one error weighing ``misplaced_weight``, which
    the channel leaving it off and the channel playing it share: the first is counted with no further
    error for the note, and the second is counted only where the writing sounds a frame of its own there.

    Attributes:
        comparison: Holds the played fields against the written ones.
        misplaced_weight: What a misplaced note weighs, a channel-frame played otherwise weighing one.
        counted: The channel-frames counted.
        wrong: The weighted errors among them.
        written: The channel-frames the writing sounds.
        missed: The written channel-frames the conversion leaves silent.
        played: The channel-frames the conversion sounds.
        spurious: The played channel-frames the writing leaves silent.
        misplaced: The written notes played at their pitch on another channel kind.
        asked: Per field, the counted channel-frames both sides sound.
        disagreed: Per field, those of them where it disagrees.
    """

    comparison: FieldComparison
    misplaced_weight: float
    counted: int = 0
    wrong: float = 0.0
    written: int = 0
    missed: int = 0
    played: int = 0
    spurious: int = 0
    misplaced: int = 0
    asked: Dict[str, int] = field(default_factory=dict)
    disagreed: Dict[str, int] = field(default_factory=dict)

    def add(self, pairs: Sequence[FramePair]) -> None:
        """Counts one frame's channel-frames, the misplaced notes among them first."""
        misplacements = Misplacements.of(pairs)
        self.misplaced += len(misplacements.missing)
        self.wrong += self.misplaced_weight * len(misplacements.missing)
        for index, pair in enumerate(pairs):
            if misplacements.passes_through(index):
                self._count_misplaced(pair, lost=index in misplacements.missing, taken=index in misplacements.added)
            else:
                self._count_plain(pair)

    def judgment(self) -> Optional[Judgment]:
        """The weighted errors per counted channel-frame, and the readings behind them.

        Returns:
            Optional[Judgment]: The judgment, or ``None`` where neither side sounded a frame to count.
        """
        if not self.counted:
            return None

        components: Dict[str, float] = {}
        if self.written:
            components[MISSED] = self.missed / self.written
            components[MISPLACED] = self.misplaced / self.written

        if self.played:
            components[SPURIOUS] = self.spurious / self.played

        for name, asked in self.asked.items():
            components[name] = self.disagreed[name] / asked

        return Judgment(score=self.wrong / self.counted, components=components)

    def _count_plain(self, pair: FramePair) -> None:
        """Counts a channel-frame no misplaced note passes through: right where both sound it and every field agrees."""
        if not (pair.written_sounds or pair.played_sounds):
            return

        self.counted += 1
        self.written += pair.written_sounds
        self.played += pair.played_sounds
        self.missed += pair.written_sounds and not pair.played_sounds
        self.spurious += pair.played_sounds and not pair.written_sounds
        if not (pair.written_sounds and pair.played_sounds):
            self.wrong += 1
            return

        agreements = self.comparison.agreements(pair.written, pair.played)
        self._count_fields(agreements)
        self.wrong += not all(agreements.values())

    def _count_misplaced(self, pair: FramePair, *, lost: bool, taken: bool) -> None:
        """Counts a channel-frame a misplaced note passes through, with the errors of its own it still holds.

        Args:
            pair: The channel-frame.
            lost: Whether its written note is the misplaced one, played on another channel kind.
            taken: Whether the note it plays is another channel's misplaced note.
        """
        self.written += pair.written_sounds
        self.played += pair.played_sounds
        if taken and not pair.written_sounds:
            return

        self.counted += 1
        self.wrong += (pair.missing and not lost) or (pair.added and not taken)

    def _count_fields(self, agreements: Dict[str, bool]) -> None:
        for name, agrees in agreements.items():
            self.asked[name] = self.asked.get(name, 0) + 1
            self.disagreed[name] = self.disagreed.get(name, 0) + (not agrees)


class TranscriptionReferee:
    """Reads how much of a sound written as NES frames its conversion plays as written.

    A channel-frame counts where the writing or the conversion sounds it, so a channel the writing
    leaves silent and the conversion sounds counts against it, however quiet: this reading says what
    went wrong, and the audio referees say how much it shows. A counted channel-frame is played as
    written where both sides sound it and every field the channel takes agrees:

    - the note;
    - the duty, read as the timbre it sounds, 25% and 75% being one;
    - the noise's period and mode;
    - the volume within ``volume_tolerance`` steps, read at the sound's own level, so the working
      level the conversion chose is charged once, by the balance's ``scale``.

    The two pulses are read across straight or crossed, whichever disagrees less (see ``Transcript``).
    A written note played at its pitch on another channel kind, such as a bass on a pulse, is wrong but
    milder than a wrong note, so it is one error weighing ``misplaced_weight`` of a channel-frame played
    otherwise (see ``Tally``).

    The score is the weighted errors per counted channel-frame: zero where every one is played as
    written, one where every one is played otherwise. Its readings, each a share where zero is closest:

    - ``missed``: the written channel-frames the conversion leaves silent;
    - ``misplaced``: the written channel-frames whose note another channel kind plays;
    - ``spurious``: the played channel-frames the writing leaves silent;
    - ``note``, ``duty``, ``volume``, ``period``, ``mode``: the channel-frames both sides sound where that
      field disagrees.
    """

    def __init__(self, *, volume_tolerance: int, misplaced_weight: float) -> None:
        self._volume_tolerance = volume_tolerance
        self._misplaced_weight = misplaced_weight

    @property
    def name(self) -> str:
        return TRANSCRIPTION_REFEREE

    def judge(self, truth: Truth, reconstruction: Reconstruction) -> Optional[Judgment]:
        """The weighted errors per counted channel-frame ``reconstruction`` plays otherwise than ``truth`` writes it.

        Returns:
            Optional[Judgment]: The judgment, or ``None`` for a sound written as no frames.
        """
        if not truth.instructions:
            return None

        played_streams = reconstruction.instructions
        length = common_length(*truth.instructions.values(), *played_streams.values())
        comparison = FieldComparison(volume_tolerance=self._volume_tolerance, scale=effective_scale(reconstruction))
        transcript = Transcript(
            written=channel_streams(truth.instructions, length),
            played=channel_streams(played_streams, length),
            reader=NoteReader(reconstruction.config),
            comparison=comparison,
        )
        tally = Tally(comparison=comparison, misplaced_weight=self._misplaced_weight)
        for frame in range(length):
            tally.add(transcript.pairs(frame))

        return tally.judgment()
