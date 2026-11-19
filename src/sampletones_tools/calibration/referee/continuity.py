import math
from dataclasses import dataclass
from typing import Dict, Final, List, Optional, Sequence, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions import Reconstruction
from sampletones_tools.calibration.corpus.truth import PitchLine, Truth, sounding_pitches

from .frames import common_length
from .pitch import SEMITONES_PER_OCTAVE
from .protocol import Judgment

CONTINUITY_REFEREE: Final[str] = "continuity"
HANDOVERS: Final[str] = "handovers"
FRAGMENTS: Final[str] = "fragments"
REFERENCE_FREQUENCY: Final[float] = 440.0

Answer = Optional[ChannelName]


@dataclass(frozen=True)
class NoteSpan:
    """A note of a line: the frames it holds one pitch through, ``end`` exclusive."""

    start: int
    end: int
    target: float


class ContinuityReferee:
    """Reads whether each note of a sound comes back as one continuous sound on one channel.

    A note is a run of frames a line of the sound holds one pitch through. In each of its frames the
    note is answered by the tonal channel the conversion sounds closest to it, or by none. A note
    heard as one instrument is answered by one channel throughout.

    The score is the excess events per note: changes of the answering channel (``handovers``), and
    the separate sounding runs beyond the first (``fragments`` less one), for example a triangle
    note picked up by a pulse halfway or a note interrupted by a dropout.
    """

    @property
    def name(self) -> str:
        return CONTINUITY_REFEREE

    def judge(self, truth: Truth, reconstruction: Reconstruction) -> Optional[Judgment]:
        """How continuously ``reconstruction`` answers the notes of ``truth``.

        Returns:
            Optional[Judgment]: The judgment, or ``None`` for a sound whose lines hold no note.
        """
        played = {
            channel: line
            for channel, line in sounding_pitches(reconstruction.instructions, reconstruction.config).items()
            if line
        }
        counts: List[Tuple[int, int]] = []
        for line in truth.pitches.values():
            length = common_length(line, *played.values())
            for note in note_spans(line[:length]):
                answers = [_answer(played, frame, note.target) for frame in range(note.start, note.end)]
                counts.append((_handovers(answers), _fragments(answers)))

        if not counts:
            return None

        handovers = sum(count for count, _ in counts) / len(counts)
        fragments = sum(count for _, count in counts) / len(counts)
        return Judgment(
            score=handovers + max(fragments - 1.0, 0.0), components={HANDOVERS: handovers, FRAGMENTS: fragments}
        )


def note_spans(line: PitchLine) -> List[NoteSpan]:
    """The notes of a line: its maximal runs of sounding frames on one semitone."""
    spans: List[NoteSpan] = []
    start: Optional[int] = None
    for frame, frequency in enumerate([*line, None]):
        if start is not None and (frequency is None or _semitone(frequency) != _semitone(line[start])):
            target = line[start]
            if target is not None:
                spans.append(NoteSpan(start=start, end=frame, target=target))
            start = None
        if start is None and frequency is not None:
            start = frame

    return spans


def _semitone(frequency: Optional[float]) -> Optional[int]:
    if frequency is None:
        return None

    return round(SEMITONES_PER_OCTAVE * math.log2(frequency / REFERENCE_FREQUENCY))


def _answer(played: Dict[ChannelName, PitchLine], frame: int, target: float) -> Answer:
    """The sounding tonal channel closest to ``target`` in the frame, or ``None`` where none sounds."""
    sounding: List[Tuple[float, ChannelName]] = []
    for channel, line in played.items():
        frequency = line[frame]
        if frequency is not None:
            sounding.append((abs(math.log2(frequency / target)), channel))

    return min(sounding)[1] if sounding else None


def _handovers(answers: Sequence[Answer]) -> int:
    heard = [answer for answer in answers if answer is not None]
    return sum(previous != current for previous, current in zip(heard, heard[1:]))


def _fragments(answers: Sequence[Answer]) -> int:
    return sum(
        1 for index, answer in enumerate(answers) if answer is not None and (index == 0 or answers[index - 1] is None)
    )
