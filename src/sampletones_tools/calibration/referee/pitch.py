import math
from dataclasses import dataclass, field
from typing import Dict, Final, List, Optional, Sequence

from sampletones_core.reconstructions import Reconstruction
from sampletones_tools.calibration.corpus.truth import PitchLine, Truth, sounding_pitches

from .frames import common_length
from .protocol import Judgment

PITCH_REFEREE: Final[str] = "pitch"
OCTAVE: Final[str] = "octave"
SEMITONE: Final[str] = "semitone"
SILENT: Final[str] = "silent"
WRONG: Final[str] = "wrong"
CENTS: Final[str] = "cents"
EXACT: Final[str] = "exact"

CENTS_PER_SEMITONE: Final[float] = 100.0
SEMITONES_PER_OCTAVE: Final[int] = 12
CLASSES: Final[Sequence[str]] = (OCTAVE, SEMITONE, SILENT, WRONG)


@dataclass
class PitchTally:
    """The sounding frames of a sound's pitch lines, by how the conversion answers each."""

    frames: int = 0
    classes: Dict[str, int] = field(default_factory=dict)
    exact_cents: List[float] = field(default_factory=list)

    def add(self, target: float, heard: Sequence[float]) -> None:
        """Counts one frame a line sounds ``target`` in, against the frequencies the conversion sounds then."""
        self.frames += 1
        if not heard:
            self._count(SILENT)
            return

        offsets = [CENTS_PER_SEMITONE * SEMITONES_PER_OCTAVE * math.log2(frequency / target) for frequency in heard]
        steps = [round(offset / CENTS_PER_SEMITONE) for offset in offsets]
        if 0 in steps:
            self._count(EXACT)
            self.exact_cents.append(min(abs(offset) for offset, step in zip(offsets, steps) if step == 0))
        elif any(step % SEMITONES_PER_OCTAVE == 0 for step in steps):
            self._count(OCTAVE)
        elif any(abs(step) == 1 for step in steps):
            self._count(SEMITONE)
        else:
            self._count(WRONG)

    def judgment(self) -> Optional[Judgment]:
        """One minus the share of frames answered on pitch, with the share of every other answer behind it.

        Returns:
            Optional[Judgment]: The judgment, or ``None`` where no line sounded a frame.
        """
        if not self.frames:
            return None

        components = {name: self.classes.get(name, 0) / self.frames for name in CLASSES}
        if self.exact_cents:
            components[CENTS] = sum(self.exact_cents) / len(self.exact_cents)

        return Judgment(score=1.0 - self.classes.get(EXACT, 0) / self.frames, components=components)

    def _count(self, name: str) -> None:
        self.classes[name] = self.classes.get(name, 0) + 1


class PitchReferee:
    """Reads whether a conversion sounds the pitches its reference sound's lines sound.

    Every frame a line sounds in is answered by the tonal channels the conversion sounds then: on pitch
    where one stands within half a semitone of the line, an octave off where one names the line's note
    in another octave, a semitone off, wrong for any other note, or silent where no tonal channel
    sounds. The closest answer counts, so a line is answered by whichever channel carries it.

    The score is the share of frames not answered on pitch. The readings behind it are the share of
    each other answer and the mean distance in cents of the answers on pitch (``cents``).
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
            for frame in range(common_length(line, *played)):
                target = line[frame]
                if target is not None:
                    tally.add(target, _heard(played, frame))

        return tally.judgment()


def _heard(played: Sequence[PitchLine], frame: int) -> List[float]:
    heard: List[Optional[float]] = [line[frame] for line in played]
    return [frequency for frequency in heard if frequency is not None]
