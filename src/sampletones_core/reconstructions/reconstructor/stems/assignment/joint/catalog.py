from dataclasses import dataclass
from typing import Dict, Final, FrozenSet, List, Optional, Self, Tuple

import numpy as np

from sampletones_core.constants.enums import GeneratorClassName
from sampletones_core.constants.general import MAX_VOLUME, MIN_VOLUME
from sampletones_core.generators import GeneratorUnion
from sampletones_core.instructions import InstructionUnion, NoiseInstruction, PulseInstruction, TriangleInstruction
from sampletones_core.reconstructions.reconstructor.candidates import CandidateProvider
from sampletones_core.reconstructions.reconstructor.window.surroundings import NoteKey
from sampletones_shared.array import to_numpy

SILENT_NOTE: Final[int] = -1
NO_TIMBRE: Final[int] = 0
SILENT_VOLUME: Final[int] = 0
NOISE_MODES: Final[int] = 2
HALF_VOLUME_STEP: Final[float] = 0.5
ALIKE_DUTY_CYCLES: Final[Dict[int, FrozenSet[int]]] = {1: frozenset({1, 3}), 3: frozenset({1, 3})}


@dataclass(frozen=True)
class RowSound:
    """What a library row sounds, as the joint assignment names it: a note, a timbre within it and a volume.

    A note is what a listener names: a pulse's or the triangle's pitch, or the noise's period together
    with its mode, ``NOISE_MODES`` notes to a period. A timbre is what one note may still change: a
    pulse's duty cycle. The triangle sounds one level, which reads as full volume. Silence sounds
    ``SILENT_NOTE`` at ``SILENT_VOLUME``.

    Attributes:
        note: The note.
        timbre: The timbre within the note, ``NO_TIMBRE`` for a kind sounding one.
        volume: The volume.
    """

    note: int
    timbre: int
    volume: int

    @classmethod
    def of(cls, instruction: InstructionUnion) -> Self:
        """What ``instruction`` sounds.

        Raises:
            TypeError: If the instruction is of an unknown kind.
        """
        if not instruction.on:
            return cls(note=SILENT_NOTE, timbre=NO_TIMBRE, volume=SILENT_VOLUME)

        match instruction:
            case PulseInstruction():
                return cls(note=instruction.pitch, timbre=instruction.duty_cycle, volume=instruction.volume)
            case TriangleInstruction():
                return cls(note=instruction.pitch, timbre=NO_TIMBRE, volume=MAX_VOLUME)
            case NoiseInstruction():
                note = NOISE_MODES * instruction.period + int(instruction.short)
                return cls(note=note, timbre=NO_TIMBRE, volume=instruction.volume)
            case _:
                raise TypeError(f"Unknown instruction {instruction!r}")


@dataclass(frozen=True)
class UnitRow:
    """The row a fitted level of one sounds for a note in a timbre: the loudest row the catalog holds of it.

    A fit scales the unit row's power by a level. A row's power grows with the square of its volume,
    so a row of volume ``v`` sounds the level ``(v / V)²`` against a unit of volume ``V``, and a level
    ``l`` sounds the volume ``V * sqrt(l)``. The highest level a channel reaches is full volume's.

    Attributes:
        row: The unit row.
        volume: The unit row's volume, at least the quietest a sounding row plays.
    """

    row: int
    volume: int

    @property
    def full_level(self) -> float:
        """The level sounding the note at full volume."""
        return self.level_of(MAX_VOLUME)

    def level_of(self, volume: int) -> float:
        """The level a row of the note and timbre at ``volume`` sounds against the unit."""
        return (volume / self.volume) ** 2

    def volume_at(self, level: float) -> float:
        """The volume a fitted ``level`` sounds the note at, zero for a level of zero or under."""
        return float(self.volume * np.sqrt(max(level, 0.0)))


@dataclass(frozen=True)
class KindCatalog:
    """One kind of channel's library rows, each read as the note, the timbre and the volume it sounds.

    Every row's power and feature values are read at unit drive. The rows of one note in one timbre
    differ in volume alone, so the search moves along a note's rows to change its level or its timbre.

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

        sounds = [RowSound.of(instruction) for instruction in candidates.instructions]
        return cls(
            kind=generator.class_name(),
            generator=generator,
            instructions=candidates.instructions,
            powers=np.asarray(to_numpy(candidates.powers), dtype=np.float64),
            features=np.asarray(to_numpy(provider.features_of(candidates.powers)), dtype=np.float64),
            notes=np.array([sound.note for sound in sounds], dtype=np.int64),
            timbres=np.array([sound.timbre for sound in sounds], dtype=np.int64),
            volumes=np.array([sound.volume for sound in sounds], dtype=np.int64),
            silence=candidates.instructions.index(silence),
            rows_by_instruction={instruction: row for row, instruction in enumerate(candidates.instructions)},
        )

    @property
    def sounded_notes(self) -> List[int]:
        """Every note the rows sound, ascending."""
        return sorted({int(note) for note in self.notes if note != SILENT_NOTE})

    def rows_of(self, note: int) -> np.ndarray:
        """Every row sounding ``note``, in catalog order."""
        return np.flatnonzero(self.notes == note)

    def rows_in(self, note: int, timbre: int) -> np.ndarray:
        """Every row sounding ``note`` in ``timbre``, in catalog order."""
        return np.flatnonzero((self.notes == note) & (self.timbres == timbre))

    def rows_like(self, row: int) -> np.ndarray:
        """Every row sounding ``row``'s note in its timbre, ``row`` included, in catalog order."""
        return self.rows_in(int(self.notes[row]), int(self.timbres[row]))

    def loudest(self, note: int, timbre: int) -> int:
        """The loudest row sounding ``note`` in ``timbre``.

        Raises:
            ValueError: If the catalog holds no row of that note in that timbre.
        """
        rows = self.rows_in(note, timbre)
        if not rows.size:
            raise ValueError(f"No {self.kind} row sounds note {note} in timbre {timbre}")

        return int(rows[int(np.argmax(self.volumes[rows]))])

    def unit_of(self, row: int) -> UnitRow:
        """The unit row of ``row``'s note and timbre."""
        return self._unit(self.loudest(int(self.notes[row]), int(self.timbres[row])))

    def units_of(self, note: int) -> List[UnitRow]:
        """The unit rows of ``note``, one for each timbre the catalog holds it in, in timbre order."""
        timbres = sorted({int(timbre) for timbre in self.timbres[self.rows_of(note)]})
        return [self._unit(self.loudest(note, timbre)) for timbre in timbres]

    def sounding_volume(self, row: int) -> int:
        """The volume ``row`` sounds at, read as at least the quietest volume a sounding row plays.

        A level against the row divides by its volume, which the floor keeps nonzero.
        """
        return max(int(self.volumes[row]), MIN_VOLUME)

    def nearest(self, row: int, volume: float) -> int:
        """The row of ``row``'s note and timbre whose volume lies nearest ``volume``.

        A volume under half a step rounds to silence, so the silent row answers it. Of two volumes
        equally near, the one earlier in catalog order answers.
        """
        if volume < HALF_VOLUME_STEP:
            return self.silence

        rows = self.rows_like(row)
        return int(rows[int(np.argmin(np.abs(self.volumes[rows] - volume)))])

    def neighbors(self, row: int, count: int) -> List[int]:
        """The ``count`` rows of ``row``'s note and timbre whose volumes lie nearest its own, nearest first.

        Rows equally near keep their catalog order.
        """
        rows = self.rows_like(row)
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

    def _unit(self, row: int) -> UnitRow:
        """``row`` as the unit of its note and timbre."""
        return UnitRow(row=row, volume=self.sounding_volume(row))


def alike_timbres(timbre: int) -> FrozenSet[int]:
    """The pulse duty cycles that sound alike to ``timbre``, itself included: 25% and 75% share a spectrum."""
    return ALIKE_DUTY_CYCLES.get(timbre, frozenset({timbre}))
