from dataclasses import dataclass
from typing import Dict, Final, List, Mapping, Optional, Self, Tuple

import numpy as np

from sampletones_core.constants.enums import GeneratorClassName
from sampletones_core.fft import Fragment
from sampletones_core.reconstructions.reconstructor.matching import FrameMatcher
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.catalog import KindCatalog
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.fit import FitTarget, fitted_levels
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.layout import StemLayout
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.proposals import (
    FREE_FIT_START,
    NoteDictionary,
)

READING_UPDATES: Final[int] = 60
FREE_TRIANGLE_REACH: Final[float] = 64.0
RUN_SHARE: Final[float] = 0.02
STANDING_SHARE: Final[float] = 0.3
TRIANGLE: Final[GeneratorClassName] = GeneratorClassName.TRIANGLE_GENERATOR


@dataclass(frozen=True)
class FrameReading:
    """Where a frame's bass stands against the triangle's one level, if a triangle line holds it.

    Attributes:
        level: How loud the bass sounds against the level the stem plays the triangle at, as an
            amplitude.
        note: The triangle note the bass is centered on.
    """

    level: float
    note: int


@dataclass(frozen=True)
class TriangleReader:
    """Reads a stem's frames for the level a triangle line in them stands at.

    Every note the stem's channels may sound is fitted to a frame at once, as the joint assignment's
    first step does, with the triangle free to sound at up to ``FREE_TRIANGLE_REACH`` times its own
    level. A triangle line then takes the level it stands at in the recording. A note sliding or
    detuned between two of the library's notes spreads over its neighbors, so neighboring triangle
    notes each holding at least ``RUN_SHARE`` of the fitted power form one run. The lowest run holding
    at least ``STANDING_SHARE`` of it is the bass, and the square root of its summed level, against
    the level the stem drives the triangle at, is the frame's reading.

    Attributes:
        dictionary: The atoms of every note the stem may sound.
        caps: Each atom's highest level, the triangle's raised.
        triangle: Which atoms are triangle notes.
        natural: The level the stem plays the triangle at, as an atom level.
        matcher: The matching machinery whose criterion the fit measures with.
    """

    dictionary: NoteDictionary
    caps: np.ndarray
    triangle: np.ndarray
    natural: float
    matcher: FrameMatcher

    @classmethod
    def of(
        cls,
        layout: StemLayout,
        catalogs: Mapping[GeneratorClassName, KindCatalog],
        matcher: FrameMatcher,
    ) -> Self:
        """The reader of a stem whose channels include the triangle.

        Raises:
            ValueError: If the stem plays no triangle.
        """
        slots = layout.of_kind(TRIANGLE)
        if not slots:
            raise ValueError(f"Stem {layout.stem_id} plays no triangle to read a level from")

        dictionary = NoteDictionary.of(layout, catalogs)
        triangle = np.array([kind == TRIANGLE for kind in dictionary.kinds], dtype=bool)
        natural = sum(1.0 / slot.drive**2 for slot in slots)
        return cls(
            dictionary=dictionary,
            caps=np.where(triangle, FREE_TRIANGLE_REACH * natural, dictionary.caps),
            triangle=triangle,
            natural=natural,
            matcher=matcher,
        )

    def read(self, fragment: Fragment) -> Optional[FrameReading]:
        """Where one frame's bass stands against the triangle's level, or ``None`` where no triangle run holds it."""
        target = FitTarget.of(fragment, self.matcher.scorer.criterion)
        levels = fitted_levels(
            target, self.dictionary.features, self.caps, start=FREE_FIT_START, updates=READING_UPDATES
        )
        strengths = levels * self.dictionary.powers
        total = float(strengths.sum())
        if total <= 0.0:
            return None

        notes = self._triangle_notes(levels, strengths)
        for run in _runs([note for note, (_, strength) in sorted(notes.items()) if strength >= RUN_SHARE * total]):
            if sum(notes[note][1] for note in run) >= STANDING_SHARE * total:
                level = sum(notes[note][0] for note in run)
                return FrameReading(
                    level=float(np.sqrt(level / self.natural)),
                    note=max(run, key=lambda note: notes[note][1]),
                )

        return None

    def _triangle_notes(self, levels: np.ndarray, strengths: np.ndarray) -> Dict[int, Tuple[float, float]]:
        """Each triangle note's fitted level and power."""
        notes: Dict[int, Tuple[float, float]] = {}
        for atom in np.flatnonzero(self.triangle):
            note = int(self.dictionary.notes[atom])
            level, strength = notes.get(note, (0.0, 0.0))
            notes[note] = (level + float(levels[atom]), strength + float(strengths[atom]))

        return notes


def _runs(notes: List[int]) -> List[List[int]]:
    """``notes``, ascending, split where two of them lie more than a semitone apart."""
    runs: List[List[int]] = []
    for note in notes:
        if runs and note - runs[-1][-1] <= 1:
            runs[-1].append(note)
        else:
            runs.append([note])

    return runs
