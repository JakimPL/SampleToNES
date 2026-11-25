from dataclasses import dataclass
from itertools import groupby, pairwise
from typing import Dict, Final, List, Optional, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions import Reconstruction
from sampletones_tools.calibration.corpus.truth import PitchLine, Truth, sounding_pitches

from .frames import line_within
from .intervals import line_semitones, octaves_between
from .protocol import Judgment

CONTINUITY_REFEREE: Final[str] = "continuity"
HANDOVERS: Final[str] = "handovers"
FRAGMENTS: Final[str] = "fragments"
WHOLE_NOTE_FRAGMENTS: Final[int] = 1

Answer = Optional[ChannelName]


@dataclass(frozen=True)
class NoteSpan:
    """A note of a line: the frames it holds one pitch through, ``end`` exclusive.

    Attributes:
        start: The note's first frame.
        end: The frame after its last.
        target: The frequency its first frame sounds, which every frame of it is answered against.
    """

    start: int
    end: int
    target: float


@dataclass(frozen=True)
class NoteAnswers:
    """Which channel answers a note in each of its frames, ``None`` where no tonal channel sounds."""

    answers: Tuple[Answer, ...]

    @property
    def handovers(self) -> int:
        """How many times the answering channel changes, a gap between two channels counting one change."""
        heard = [answer for answer in self.answers if answer is not None]
        return sum(previous != current for previous, current in pairwise(heard))

    @property
    def fragments(self) -> int:
        """How many separate runs of frames answer the note: one for a note heard whole, none for a silent one.

        A run starts at each answered frame whose frame before is unanswered, the note's first frame
        included.
        """
        runs = 0
        for previous, current in pairwise((None, *self.answers)):
            runs += previous is None and current is not None

        return runs

    @property
    def extra_fragments(self) -> int:
        """How many runs answer the note beyond the one of a note heard whole, none for a silent note."""
        return max(self.fragments - WHOLE_NOTE_FRAGMENTS, 0)


class ContinuityReferee:
    """Reads whether each note of a sound comes back as one continuous sound on one channel.

    A note is a run of frames a line of the sound holds one pitch through (see ``note_spans``). In each
    of its frames the note is answered by the sounding tonal channel nearest its pitch, however far,
    or by none (see ``answer_at``). A note heard as one instrument is answered by one channel
    throughout, in one run.

    The score is the excess events per note, zero being closest: the mean changes of the answering
    channel (``handovers``), plus the mean of each note's sounding runs beyond its first
    (``NoteAnswers.extra_fragments``). A triangle note picked up by a pulse halfway is a handover, and a
    note interrupted by a dropout is a fragment. A note left silent adds no excess event, since the
    ``pitch`` referee charges it as silent. The ``fragments`` reading is the mean of the runs per note,
    one where every note is heard whole.
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
        notes: List[NoteAnswers] = []
        for line in truth.pitches.values():
            notes.extend(_answered_notes(line, played))

        if not notes:
            return None

        handovers = sum(note.handovers for note in notes) / len(notes)
        fragments = sum(note.fragments for note in notes) / len(notes)
        extra_fragments = sum(note.extra_fragments for note in notes) / len(notes)
        return Judgment(
            score=handovers + extra_fragments,
            components={HANDOVERS: handovers, FRAGMENTS: fragments},
        )


def note_spans(line: PitchLine) -> List[NoteSpan]:
    """The notes of a line: its maximal runs of sounding frames on one semitone.

    Consecutive frames nearest one semitone are one note held, so grouping the frames by the semitone
    each sounds yields the notes, and the silent groups fall away.
    """
    semitones = line_semitones(line)
    spans: List[NoteSpan] = []
    for _, grouped in groupby(range(len(line)), key=semitones.__getitem__):
        frames = list(grouped)
        target = line[frames[0]]
        if target is not None:
            spans.append(NoteSpan(start=frames[0], end=frames[-1] + 1, target=target))

    return spans


def answer_at(played: Dict[ChannelName, PitchLine], frame: int, target: float) -> Answer:
    """The sounding tonal channel nearest ``target`` in the frame, or ``None`` where none sounds.

    Nearness is the distance in octaves, and a tie goes to the channel whose name sorts first, so two
    pulses in unison answer as pulse 1.
    """
    sounding: List[Tuple[float, ChannelName]] = []
    for channel, line in played.items():
        frequency = line[frame]
        if frequency is not None:
            sounding.append((abs(octaves_between(frequency, target)), channel))

    return min(sounding)[1] if sounding else None


def _answered_notes(line: PitchLine, played: Dict[ChannelName, PitchLine]) -> List[NoteAnswers]:
    """Every note of ``line`` within the frames the conversion plays, with the channel answering each frame."""
    return [
        NoteAnswers(answers=tuple(answer_at(played, frame, note.target) for frame in range(note.start, note.end)))
        for note in note_spans(line_within(line, played.values()))
    ]
