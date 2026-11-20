from dataclasses import dataclass, field
from typing import Dict, Final, List, Optional, Self, Sequence, Set, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import NoiseInstruction, PulseInstruction, TriangleInstruction
from sampletones_core.reconstructions import Reconstruction
from sampletones_tools.calibration.corpus.truth import Truth

from .frames import Frame, channel_streams, common_length, sounds
from .notes import Note, NoteReader
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
INVERTED_DUTY_CYCLES: Final[Dict[int, int]] = {3: 1}
SOLE_CHANNELS: Final[Tuple[ChannelName, ...]] = (ChannelName.TRIANGLE, ChannelName.NOISE)


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
    def missing(self) -> bool:
        """Whether the written note is absent from what this channel plays."""
        return self.written_note is not None and self.played_note != self.written_note

    @property
    def added(self) -> bool:
        """Whether this channel plays a note the writing leaves off it."""
        return self.played_note is not None and self.written_note != self.played_note


@dataclass(frozen=True)
class Misplacements:
    """The written notes of one frame played at their pitch on another channel kind.

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
            if not pair.missing or pair.written_note is None:
                continue

            for other, candidate in enumerate(pairs):
                if other in added or other == index or not candidate.added or candidate.played_note is None:
                    continue
                if (
                    candidate.played_note.semitone == pair.written_note.semitone
                    and candidate.played_note.kind != pair.written_note.kind
                ):
                    missing.add(index)
                    added.add(other)
                    break

        return cls(missing=missing, added=added)


@dataclass
class Tally:
    """The channel-frames a transcription counts, and those that miss in each way."""

    counted: int = 0
    wrong: float = 0.0
    written: int = 0
    missed: int = 0
    played: int = 0
    spurious: int = 0
    misplaced: int = 0
    asked: Dict[str, int] = field(default_factory=dict)
    disagreed: Dict[str, int] = field(default_factory=dict)

    def add(
        self,
        pairs: Sequence[FramePair],
        *,
        volume_tolerance: int,
        scale: float,
        misplaced_weight: float,
    ) -> None:
        """Counts one frame's channel-frames, where the writing or the conversion sounds them.

        A written note played at its pitch on another channel kind is one error of
        ``misplaced_weight``, so the channel leaving it off and the channel playing it count it once,
        and a channel sounding only that note counts no further frame.
        """
        misplacements = Misplacements.of(pairs)
        self.misplaced += len(misplacements.missing)
        self.wrong += misplaced_weight * len(misplacements.missing)
        for index, pair in enumerate(pairs):
            if index in misplacements.missing or index in misplacements.added:
                self._add_misplaced(pair, index in misplacements.missing, index in misplacements.added)
            else:
                self._add_pair(pair, volume_tolerance=volume_tolerance, scale=scale)

    def _add_pair(self, pair: FramePair, *, volume_tolerance: int, scale: float) -> None:
        written_sounds, played_sounds = sounds(pair.written), sounds(pair.played)
        if not written_sounds and not played_sounds:
            return

        self.counted += 1
        self.written += written_sounds
        self.played += played_sounds
        self.missed += written_sounds and not played_sounds
        self.spurious += played_sounds and not written_sounds
        if not (written_sounds and played_sounds):
            self.wrong += 1
            return

        fields = compared_fields(pair.written, pair.played, volume_tolerance=volume_tolerance, scale=scale)
        for name, agrees in fields.items():
            self.asked[name] = self.asked.get(name, 0) + 1
            self.disagreed[name] = self.disagreed.get(name, 0) + (not agrees)

        self.wrong += not all(fields.values())

    def _add_misplaced(self, pair: FramePair, lost: bool, taken: bool) -> None:
        """Counts a channel-frame a misplaced note passes through, with the errors the note leaves on it."""
        written_sounds, played_sounds = sounds(pair.written), sounds(pair.played)
        self.written += written_sounds
        self.played += played_sounds
        if not written_sounds and taken:
            return

        self.counted += 1
        self.wrong += (pair.missing and not lost) or (pair.added and not taken)

    def judgment(self) -> Optional[Judgment]:
        """The share of counted channel-frames played otherwise than written, and the readings behind it.

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


class TranscriptionReferee:
    """Reads how much of a sound written as NES frames its conversion plays as written.

    A channel-frame counts where the writing or the conversion sounds it, so a channel the writing
    leaves silent and the conversion sounds counts against it. A counted frame is played as written
    where both sound it and every field the channel takes agrees: the duty as the timbre it sounds,
    25% and 75% being one, and the volume within the tolerance once the working-level scale is taken
    back out, which leaves the scale itself to the balance reading. The two pulses sound one mix
    whichever of them carries which line, so each frame pairs them the way fewer fields disagree.
    A written note played at its pitch on another channel kind, such as a bass on a pulse, is one
    error weighing ``misplaced_weight`` of a frame played otherwise.

    The score is the weighted share of counted channel-frames played otherwise. The readings behind it
    are the share of written frames left silent (``missed``), the share of written frames played on
    another channel kind (``misplaced``), the share of played frames the writing leaves silent
    (``spurious``), and for each field, the share of frames both sound where it disagrees.
    """

    def __init__(self, *, volume_tolerance: int, misplaced_weight: float) -> None:
        self._volume_tolerance = volume_tolerance
        self._misplaced_weight = misplaced_weight

    @property
    def name(self) -> str:
        return TRANSCRIPTION_REFEREE

    def judge(self, truth: Truth, reconstruction: Reconstruction) -> Optional[Judgment]:
        """The share of counted channel-frames ``reconstruction`` plays otherwise than ``truth`` writes them.

        Returns:
            Optional[Judgment]: The judgment, or ``None`` for a sound written as no frames.
        """
        if not truth.instructions:
            return None

        played_streams = reconstruction.instructions
        length = common_length(*truth.instructions.values(), *played_streams.values())
        written = channel_streams(truth.instructions, length)
        played = channel_streams(played_streams, length)
        reader = NoteReader(reconstruction.config)
        scale = effective_scale(reconstruction)
        tally = Tally()
        for frame in range(length):
            channels = self._paired_pulses(written, played, frame, scale)
            channels.extend((channel, channel) for channel in SOLE_CHANNELS)
            pairs = [
                FramePair(
                    written=written[written_channel][frame],
                    played=played[played_channel][frame],
                    written_note=reader.note(written_channel, written[written_channel][frame]),
                    played_note=reader.note(played_channel, played[played_channel][frame]),
                )
                for written_channel, played_channel in channels
            ]
            tally.add(
                pairs,
                volume_tolerance=self._volume_tolerance,
                scale=scale,
                misplaced_weight=self._misplaced_weight,
            )

        return tally.judgment()

    def _paired_pulses(
        self,
        written: Dict[ChannelName, Tuple[Frame, ...]],
        played: Dict[ChannelName, Tuple[Frame, ...]],
        frame: int,
        scale: float,
    ) -> List[Tuple[ChannelName, ChannelName]]:
        """The written and played pulse each pulse line is read across, straight or crossed."""
        first, second = PULSES
        straight = [(first, first), (second, second)]
        crossed = [(first, second), (second, first)]
        disagreements = {
            pairing: self._disagreements(
                [(written[source][frame], played[target][frame]) for source, target in pairing],
                scale,
            )
            for pairing in (tuple(straight), tuple(crossed))
        }
        return crossed if disagreements[tuple(crossed)] < disagreements[tuple(straight)] else straight

    def _disagreements(self, pairs: List[Tuple[Frame, Frame]], scale: float) -> int:
        """How many fields disagree across the pairs, a frame sounding on one side alone counting one."""
        count = 0
        for written_frame, played_frame in pairs:
            if sounds(written_frame) and sounds(played_frame):
                fields = compared_fields(
                    written_frame,
                    played_frame,
                    volume_tolerance=self._volume_tolerance,
                    scale=scale,
                )
                count += sum(not agrees for agrees in fields.values())
            else:
                count += sounds(written_frame) != sounds(played_frame)

        return count


def timbre_of(duty_cycle: int) -> int:
    """The timbre a duty cycle sounds: 75% is the 25% wave inverted, which the ear hears as the same."""
    return INVERTED_DUTY_CYCLES.get(duty_cycle, duty_cycle)


def compared_fields(written: Frame, played: Frame, *, volume_tolerance: int, scale: float) -> Dict[str, bool]:
    """Whether each field the channel takes agrees between two sounding frames of it.

    The played volume is read at the sound's own level, times the working-level ``scale``.
    """
    match written, played:
        case PulseInstruction(), PulseInstruction():
            return {
                NOTE: written.pitch == played.pitch,
                DUTY: timbre_of(written.duty_cycle) == timbre_of(played.duty_cycle),
                VOLUME: abs(written.volume - played.volume * scale) <= volume_tolerance,
            }
        case TriangleInstruction(), TriangleInstruction():
            return {NOTE: written.pitch == played.pitch}
        case NoiseInstruction(), NoiseInstruction():
            return {
                PERIOD: written.period == played.period,
                MODE: written.short == played.short,
                VOLUME: abs(written.volume - played.volume * scale) <= volume_tolerance,
            }
        case _:
            raise TypeError(f"Frames of different channels compared: {written!r} and {played!r}")
