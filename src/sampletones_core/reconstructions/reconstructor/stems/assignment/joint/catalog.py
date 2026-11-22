from dataclasses import dataclass
from typing import Dict, Final, FrozenSet, List, Optional, Self, Sequence, Tuple

import numpy as np

from sampletones_core.constants.enums import GeneratorClassName
from sampletones_core.generators import GeneratorUnion
from sampletones_core.instructions import InstructionUnion, NoiseInstruction, PulseInstruction, TriangleInstruction
from sampletones_core.reconstructions.reconstructor.candidates import CandidateProvider
from sampletones_core.reconstructions.reconstructor.window.surroundings import NoteKey
from sampletones_shared.array import to_numpy

SILENT_NOTE: Final[int] = -1
NO_TIMBRE: Final[int] = 0
FULL_VOLUME: Final[int] = 15
NOISE_MODES: Final[int] = 2
ALIKE_DUTY_CYCLES: Final[Dict[int, FrozenSet[int]]] = {1: frozenset({1, 3}), 3: frozenset({1, 3})}


@dataclass(frozen=True)
class KindCatalog:
    """One kind of channel's library rows, grouped by the note each sounds and the timbre it sounds it in.

    A note is what a listener names: a pulse's or the triangle's pitch, or the noise's period together
    with its mode. A timbre is what one note may still change: a pulse's duty cycle. Every row is read
    at unit drive, and the search moves along a note's rows to change its level or its timbre.

    Attributes:
        kind: The generator class the rows belong to.
        generator: A generator of the class, which answers its silent instruction.
        instructions: The rows, in the order the candidate provider holds them.
        powers: Each row's power density per bin, at unit drive.
        features: Each row's feature values, at unit drive.
        notes: Each row's note, ``SILENT_NOTE`` for the silent row.
        timbres: Each row's timbre within its note.
        volumes: Each row's volume; the triangle's one level reads as full volume.
        silence: The silent row.
        rows_by_instruction: Each instruction's row.
    """

    kind: GeneratorClassName
    generator: GeneratorUnion
    instructions: Tuple[InstructionUnion, ...]
    powers: np.ndarray
    features: np.ndarray
    notes: np.ndarray
    timbres: np.ndarray
    volumes: np.ndarray
    silence: int
    rows_by_instruction: Dict[InstructionUnion, int]

    @classmethod
    def build(cls, provider: CandidateProvider, generator: GeneratorUnion) -> Self:
        """The catalog of the library rows ``provider`` holds for ``generator``'s class.

        Raises:
            ValueError: If the library lacks the class's silent instruction.
        """
        candidates = provider.candidates({generator.class_name(): generator})
        silence = generator.get_instruction_type().null_instruction()
        if silence not in candidates.instructions:
            raise ValueError(f"The library lacks the silent instruction of {generator.class_name()}")

        described = [_described(instruction) for instruction in candidates.instructions]
        return cls(
            kind=generator.class_name(),
            generator=generator,
            instructions=candidates.instructions,
            powers=np.asarray(to_numpy(candidates.powers), dtype=np.float64),
            features=np.asarray(to_numpy(provider.features_of(candidates.powers)), dtype=np.float64),
            notes=np.array([note for note, _, _ in described], dtype=np.int64),
            timbres=np.array([timbre for _, timbre, _ in described], dtype=np.int64),
            volumes=np.array([volume for _, _, volume in described], dtype=np.int64),
            silence=candidates.instructions.index(silence),
            rows_by_instruction={instruction: row for row, instruction in enumerate(candidates.instructions)},
        )

    def rows_of(self, note: int) -> np.ndarray:
        """Every row sounding ``note``, in catalog order."""
        return np.flatnonzero(self.notes == note)

    def rows_in(self, note: int, timbre: int) -> np.ndarray:
        """Every row sounding ``note`` in ``timbre``, in catalog order."""
        return np.flatnonzero((self.notes == note) & (self.timbres == timbre))

    def loudest(self, note: int, timbre: int) -> int:
        """The loudest row sounding ``note`` in ``timbre``.

        Raises:
            ValueError: If the catalog holds no row of that note in that timbre.
        """
        rows = self.rows_in(note, timbre)
        if not rows.size:
            raise ValueError(f"No {self.kind} row sounds note {note} in timbre {timbre}")

        return int(rows[int(np.argmax(self.volumes[rows]))])

    def nearest(self, row: int, volume: float) -> int:
        """The row of ``row``'s note and timbre whose volume lies nearest ``volume``; silence under half a step."""
        if volume < 0.5:
            return self.silence

        rows = self.rows_in(int(self.notes[row]), int(self.timbres[row]))
        return int(rows[int(np.argmin(np.abs(self.volumes[rows] - volume)))])

    def neighbors(self, row: int, count: int) -> List[int]:
        """The ``count`` rows of ``row``'s note and timbre whose volumes lie nearest its own, nearest first."""
        rows = self.rows_in(int(self.notes[row]), int(self.timbres[row]))
        others = rows[rows != row]
        order = np.argsort(np.abs(self.volumes[others] - self.volumes[row]), kind="stable")
        return [int(other) for other in others[order][:count]]

    def sounding(self, row: int) -> bool:
        """Whether ``row`` sounds a note."""
        return bool(self.notes[row] != SILENT_NOTE)

    def key(self, row: int) -> Optional[NoteKey]:
        """The note and timbre ``row`` sounds, or ``None`` for silence."""
        return (int(self.notes[row]), int(self.timbres[row])) if self.sounding(row) else None

    def note_name(self, row: int) -> Optional[int]:
        """The note ``row`` sounds, or ``None`` for silence."""
        return int(self.notes[row]) if self.sounding(row) else None


def alike_timbres(timbre: int) -> FrozenSet[int]:
    """The pulse duty cycles that sound alike to ``timbre``, itself included: 25% and 75% share a spectrum."""
    return ALIKE_DUTY_CYCLES.get(timbre, frozenset({timbre}))


def note_of(instruction: InstructionUnion) -> int:
    """The note an instruction sounds: a pitch, or a noise period with its mode; ``SILENT_NOTE`` when off."""
    return _described(instruction)[0]


def _described(instruction: InstructionUnion) -> Tuple[int, int, int]:
    """An instruction's note, timbre and volume."""
    if not instruction.on:
        return SILENT_NOTE, NO_TIMBRE, 0

    match instruction:
        case PulseInstruction():
            return instruction.pitch, instruction.duty_cycle, instruction.volume
        case TriangleInstruction():
            return instruction.pitch, NO_TIMBRE, FULL_VOLUME
        case NoiseInstruction():
            return NOISE_MODES * instruction.period + int(instruction.short), NO_TIMBRE, instruction.volume
        case _:
            raise TypeError(f"Unknown instruction {instruction!r}")


def strongest_rows(catalog: KindCatalog, notes: Sequence[int]) -> Dict[int, List[int]]:
    """Every note's loudest row in each timbre the catalog holds it in."""
    loudest: Dict[int, List[int]] = {}
    for note in notes:
        timbres = sorted({int(timbre) for timbre in catalog.timbres[catalog.rows_of(note)]})
        loudest[note] = [catalog.loudest(note, timbre) for timbre in timbres]

    return loudest
