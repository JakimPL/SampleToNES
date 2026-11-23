from dataclasses import dataclass, field
from typing import Dict, Final, List, Optional, Sequence

from sampletones_core.reconstructions import Reconstruction
from sampletones_shared.constants.music import OCTAVE_SEMITONES, SEMITONE_STEP
from sampletones_tools.calibration.corpus.truth import PitchLine, Truth, sounding_pitches

from .frames import line_within
from .intervals import CENTS_PER_SEMITONE, cents_between
from .protocol import Judgment

PITCH_REFEREE: Final[str] = "pitch"
OCTAVE: Final[str] = "octave"
SEMITONE: Final[str] = "semitone"
SILENT: Final[str] = "silent"
WRONG: Final[str] = "wrong"
CENTS: Final[str] = "cents"
EXACT: Final[str] = "exact"

ON_PITCH_STEP: Final[int] = 0
CLASSES: Final[Sequence[str]] = (OCTAVE, SEMITONE, SILENT, WRONG)


def answer_of(offsets: Sequence[float]) -> str:
    """How the channels sounding in a frame answer a line's pitch, from each one's offset from it in cents.

    An offset is read as its nearest semitone step, so a channel within half a semitone of the line
    stands on pitch. The answers rank on pitch (``EXACT``), an octave off (the line's note in another
    octave), a semitone off, then wrong, and the best answer any channel gives counts, so a line is
    answered by whichever channel carries it. With no channel sounding the line is silent.
    """
    steps = [_semitone_step(offset) for offset in offsets]
    if not steps:
        return SILENT

    if ON_PITCH_STEP in steps:
        return EXACT

    if any(step % OCTAVE_SEMITONES == 0 for step in steps):
        return OCTAVE

    if any(abs(step) == SEMITONE_STEP for step in steps):
        return SEMITONE

    return WRONG


@dataclass
class PitchTally:
    """The sounding frames of a sound's pitch lines, by how the conversion answers each."""

    frames: int = 0
    classes: Dict[str, int] = field(default_factory=dict)
    exact_cents: List[float] = field(default_factory=list)

    def add(self, target: float, heard: Sequence[float]) -> None:
        """Counts one frame a line sounds ``target`` in, against the frequencies the conversion sounds then."""
        self.frames += 1
        offsets = [cents_between(frequency, target) for frequency in heard]
        answer = answer_of(offsets)
        self.classes[answer] = self.classes.get(answer, 0) + 1
        if answer == EXACT:
            self.exact_cents.append(min(abs(offset) for offset in offsets if _semitone_step(offset) == ON_PITCH_STEP))

    def judgment(self) -> Optional[Judgment]:
        """One less the share of frames answered on pitch, with the share of every other answer behind it.

        Returns:
            Optional[Judgment]: The judgment, or ``None`` where no line sounded a frame.
        """
        if not self.frames:
            return None

        components = {name: self.classes.get(name, 0) / self.frames for name in CLASSES}
        if self.exact_cents:
            components[CENTS] = sum(self.exact_cents) / len(self.exact_cents)

        return Judgment(score=1.0 - self.classes.get(EXACT, 0) / self.frames, components=components)


class PitchReferee:
    """Reads whether a conversion sounds the pitches its reference sound's lines sound.

    Every frame a line sounds in, within the frames the conversion plays (see ``line_within``), is
    answered by the tonal channels the conversion sounds then (see ``answer_of``). Both sides are read
    at the frequency each frame sounds, bends included, and compared by their ratio, so the reading
    holds on any tuning.

    The score is the share of the lines' sounding frames not answered on pitch: zero where every one
    is, one where none is. Its readings, each a share where zero is closest: ``octave``, ``semitone``,
    ``wrong`` and ``silent``, the frames answered so. Where any frame is answered on pitch, ``cents`` is
    the mean distance of those answers from the line, in cents, zero being closest.
    """

    @property
    def name(self) -> str:
        return PITCH_REFEREE

    def judge(self, truth: Truth, reconstruction: Reconstruction) -> Optional[Judgment]:
        """How the pitches ``reconstruction`` sounds answer the lines ``truth`` sounds.

        Returns:
            Optional[Judgment]: The judgment, or ``None`` for a sound whose lines sound no frame.
        """
        played = [
            line for line in sounding_pitches(reconstruction.instructions, reconstruction.config).values() if line
        ]
        tally = PitchTally()
        for line in truth.pitches.values():
            for frame, target in enumerate(line_within(line, played)):
                if target is not None:
                    tally.add(target, heard_at(played, frame))

        return tally.judgment()


def heard_at(played: Sequence[PitchLine], frame: int) -> List[float]:
    """The frequencies the conversion's lines sound in ``frame``, one per sounding line."""
    heard: List[Optional[float]] = [line[frame] for line in played]
    return [frequency for frequency in heard if frequency is not None]


def _semitone_step(offset: float) -> int:
    """The whole semitones nearest an offset in cents."""
    return round(offset / CENTS_PER_SEMITONE)
