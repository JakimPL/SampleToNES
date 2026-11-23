from dataclasses import dataclass
from operator import attrgetter
from typing import Final, List, Mapping, Optional, Self, Sequence, Tuple

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
RUN_STEP: Final[int] = 1
STANDING_SHARE: Final[float] = 0.3
TRIANGLE: Final[GeneratorClassName] = GeneratorClassName.TRIANGLE_GENERATOR


@dataclass(frozen=True)
class FrameReading:
    """Where a frame's bass stands against the triangle's one level, if a triangle line holds it.

    Attributes:
        level: How loud the bass sounds against the level the stem plays the triangle at, as an
            amplitude. It is the factor the working level moves by to bring the bass onto the triangle.
        note: The triangle note the bass is centered on.
    """

    level: float
    note: int


@dataclass(frozen=True)
class TriangleNote:
    """One triangle note as a frame's fit of every note sounds it.

    Attributes:
        note: The note.
        level: Its fitted level, against its row at unit drive.
        strength: The power its fitted level sounds, unweighted.
    """

    note: int
    level: float
    strength: float


@dataclass(frozen=True)
class TriangleRun:
    """Neighboring triangle notes a frame's fit sounds, read as the one note a bass plays.

    A note sliding or detuned between two of the library's notes spreads over its neighbors, so
    notes at most ``RUN_STEP`` semitones apart join one run. The run sounds its notes' levels and
    strengths together, and is centered on its strongest note.

    Attributes:
        notes: The run's notes, ascending.
    """

    notes: Tuple[TriangleNote, ...]

    @classmethod
    def bass(cls, notes: Sequence[TriangleNote], total: float) -> Optional[Self]:
        """The bass among the triangle ``notes`` of a fit sounding ``total``, ``None`` where no run holds it.

        The fit leaves every atom some level, so only the notes each holding at least ``RUN_SHARE`` of
        ``total`` form the runs, and a note the fit barely sounds leaves a gap between the notes beside
        it. A triangle line plays the bass, so the lowest run holding at least ``STANDING_SHARE`` of
        ``total`` is read as the bass, and a run holding less leaves it to the runs above.

        Args:
            notes: The triangle notes, ascending.
            total: The strength the fit sounds over every note of every kind.
        """
        held = [note for note in notes if note.strength >= RUN_SHARE * total]
        for run in cls.split(held):
            if run.strength >= STANDING_SHARE * total:
                return run

        return None

    @classmethod
    def split(cls, notes: Sequence[TriangleNote]) -> List[Self]:
        """``notes``, ascending, split into runs wherever two of them lie more than ``RUN_STEP`` semitones apart."""
        runs: List[List[TriangleNote]] = []
        for note in notes:
            if runs and note.note - runs[-1][-1].note <= RUN_STEP:
                runs[-1].append(note)
            else:
                runs.append([note])

        return [cls(notes=tuple(run)) for run in runs]

    @property
    def level(self) -> float:
        """The level the run's notes sound together."""
        return sum(note.level for note in self.notes)

    @property
    def strength(self) -> float:
        """The power the run's notes sound together."""
        return sum(note.strength for note in self.notes)

    @property
    def center(self) -> int:
        """The run's strongest note, the lowest of notes equally strong."""
        return max(self.notes, key=attrgetter("strength")).note

    def reading(self, natural: float) -> FrameReading:
        """The run as a frame's bass, against the level ``natural`` a stem plays the triangle at.

        Levels read in power, so the square root of their ratio reads the bass in amplitude.
        """
        return FrameReading(level=float(np.sqrt(self.level / natural)), note=self.center)


@dataclass(frozen=True)
class TriangleReader:
    """Reads a stem's frames for the level a triangle line in them stands at.

    All the notes the stem's channels may sound are fitted to a frame at once, the frame heard
    alone, as the joint assignment's first step fits it (``fitted_levels``), for
    ``READING_UPDATES`` updates. The triangle is free to sound at up to ``FREE_TRIANGLE_REACH``
    times its own level, so a triangle line takes the level it stands at in the recording. The
    triangle notes the fit sounds give the frame's bass (``TriangleRun.bass``), and the bass gives
    the frame's reading (``TriangleRun.reading``).

    Attributes:
        dictionary: The atoms of every note the stem may sound.
        caps: Each atom's highest level, the triangle's raised.
        triangle: Which atoms are triangle notes.
        natural: The level the stem plays the triangle at, as an atom level: what every triangle
            channel of the stem sounds at its drive (``StemLayout.gain``).
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
        if not layout.of_kind(TRIANGLE):
            raise ValueError(f"Stem {layout.stem_id} plays no triangle to read a level from")

        dictionary = NoteDictionary.of(layout, catalogs)
        triangle = np.array([kind == TRIANGLE for kind in dictionary.kinds], dtype=bool)
        natural = layout.gain(TRIANGLE)
        return cls(
            dictionary=dictionary,
            caps=np.where(triangle, FREE_TRIANGLE_REACH * natural, dictionary.caps),
            triangle=triangle,
            natural=natural,
            matcher=matcher,
        )

    def read(self, fragment: Fragment) -> Optional[FrameReading]:
        """Where one frame's bass stands against the triangle's level, ``None`` where no triangle run holds it.

        A fit sounding nothing holds no bass.
        """
        levels = self._fitted(fragment)
        strengths = levels * self.dictionary.powers
        total = float(strengths.sum())
        if total <= 0.0:
            return None

        bass = TriangleRun.bass(self._triangle_notes(levels, strengths), total)
        if bass is None:
            return None

        return bass.reading(self.natural)

    def _fitted(self, fragment: Fragment) -> np.ndarray:
        """Every atom's level fitted to ``fragment`` heard alone, which holds nothing before the atoms sound."""
        target = FitTarget.of(fragment, self.matcher.scorer.criterion)
        return fitted_levels(
            target,
            self.dictionary.features,
            self.caps,
            base=np.zeros_like(target.reference),
            start=FREE_FIT_START,
            updates=READING_UPDATES,
        )

    def _triangle_notes(self, levels: np.ndarray, strengths: np.ndarray) -> List[TriangleNote]:
        """Each triangle note at its fitted level and strength, ascending.

        The triangle sounds one timbre, so each of its notes is one atom, and the dictionary holds
        a kind's notes ascending.
        """
        return [
            TriangleNote(
                note=int(self.dictionary.notes[atom]), level=float(levels[atom]), strength=float(strengths[atom])
            )
            for atom in np.flatnonzero(self.triangle)
        ]
