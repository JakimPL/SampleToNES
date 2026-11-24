from dataclasses import dataclass
from typing import Dict, Final, List, Mapping, Self, Tuple

import numpy as np

from sampletones_core.constants.enums import GeneratorClassName
from sampletones_core.fft import Fragment
from sampletones_core.reconstructions.reconstructor.matching import FrameMatcher
from sampletones_shared.array import xp

from .batches import cheapest_row, split_by_group
from .catalog import KindCatalog, alike_timbres
from .fit import FitTarget, fitted_levels
from .hearing import FrameHearing, SteadyHearing, rows_by_place
from .layout import StemLayout

FREE_FIT_START: Final[float] = 0.05
FREE_FIT_UPDATES: Final[int] = 40
SHORTFALL_WEIGHT: Final[float] = 0.05
DOUBLED_NOTES: Final[int] = 2
PROPOSED_NOTES: Final[Dict[GeneratorClassName, int]] = {
    GeneratorClassName.PULSE_GENERATOR: 8,
    GeneratorClassName.TRIANGLE_GENERATOR: 4,
    GeneratorClassName.NOISE_GENERATOR: 3,
}

KindNote = Tuple[GeneratorClassName, int]


@dataclass(frozen=True)
class NoteStrengths:
    """How strongly a frame sounds each note of each kind, as the fit of every note at once reads it.

    A note's strength is the power its atoms' fitted levels sound it at heard alone (``HeardAtoms``),
    summed over its timbres and unweighted, so a bass counts for what it plays where the criterion's
    weights are light.

    Attributes:
        strengths: Each note's strength, keyed by its kind and note, in the dictionary's order.
    """

    strengths: Dict[KindNote, float]

    def strongest(self, kind: GeneratorClassName, count: int) -> List[int]:
        """Up to ``count`` notes of ``kind``, the strongest first, each of a strength above zero.

        Equally strong notes keep the dictionary's order, the lower note first.
        """
        notes = [note for note_kind, note in self.strengths if note_kind == kind]
        ranked = sorted(notes, key=lambda note: -self.strengths[(kind, note)])
        return [note for note in ranked[:count] if self.strengths[(kind, note)] > 0.0]


@dataclass(frozen=True)
class HeardAtoms:
    """A note dictionary's atoms as a frame heard alone hears them, each on the channel its note is heard on.

    A level of one sounds an atom's unit row on its channel, at the drive the stem gives the
    channel, and a frame heard alone reads it there as the row's power at the drive
    (``FrameHearing.unit_features``). An atom's cap is what every channel of its kind playing it at
    full volume sounds, as a level of the atom on its channel: its full level times the channel's
    ``StemLayout.gain``. The caps and the powers move with the atoms, so the most a note sounds is
    what the stem's channels play at every drive.

    An atom's power is its unit row's power heard alone on its channel
    (``FrameHearing.steady_powers``), so a note's strength is the power its fitted level sounds the
    note at, heard alone. The power sums the row's power densities over the bins, the form the
    catalog holds a row's power in. The proposal counts (``PROPOSED_NOTES``) and the triangle run's
    shares (``level.reading``) were tuned on strengths read in densities. A density weighs a partial
    by its bin's width, so where the bins widen with frequency, as under ``cqt`` and above about
    500 Hz under ``logfft``, a note's low partials weigh more than its high ones. Under ``fft`` every
    bin is as wide, and the densities rank the notes as their bin powers do.

    Attributes:
        kinds: Each atom's kind.
        notes: Each atom's note.
        features: Each atom's feature values heard alone at a level of one, one per row.
        caps: The highest level each atom may reach.
        powers: Each atom's whole power heard alone on its channel, which a fitted note's strength is
            read in.
    """

    kinds: Tuple[GeneratorClassName, ...]
    notes: np.ndarray
    features: np.ndarray
    caps: np.ndarray
    powers: np.ndarray

    def strengths(self, levels: np.ndarray) -> NoteStrengths:
        """How strongly the frame sounds each note, the atoms fitted at ``levels``."""
        strengths: Dict[KindNote, float] = {}
        for kind, note, energy in zip(self.kinds, self.notes, levels * self.powers):
            key = (kind, int(note))
            strengths[key] = strengths.get(key, 0.0) + float(energy)

        return NoteStrengths(strengths=strengths)


@dataclass(frozen=True)
class NoteDictionary:
    """One atom per note and timbre a stem's channels may sound, which a frame's levels are fitted over.

    An atom is the unit row of its note in its timbre, so a level of one sounds that row. The
    dictionary holds the atoms' rows, and a frame heard alone hears them (``heard``): a row's sound
    belongs to the row on a channel. The atoms stand kind by kind in name order, each kind's notes
    ascending and each note's timbres ascending.

    Attributes:
        layout: The stem's channels.
        kinds: Each atom's kind.
        notes: Each atom's note.
        rows: Each atom's unit row.
        full_levels: The level of each atom sounding its note at full volume on one channel.
    """

    layout: StemLayout
    kinds: Tuple[GeneratorClassName, ...]
    notes: np.ndarray
    rows: np.ndarray
    full_levels: np.ndarray

    @classmethod
    def of(cls, layout: StemLayout, catalogs: Mapping[GeneratorClassName, KindCatalog]) -> Self:
        """The dictionary of every note ``layout``'s channels may sound.

        A stem whose kinds sound no note has a dictionary of no atom.
        """
        kinds: List[GeneratorClassName] = []
        notes: List[int] = []
        rows: List[int] = []
        full_levels: List[float] = []
        for kind in sorted(layout.kinds):
            catalog = catalogs[kind]
            for note in catalog.sounded_notes:
                for unit in catalog.units_of(note):
                    kinds.append(kind)
                    notes.append(note)
                    rows.append(unit.row)
                    full_levels.append(unit.full_level)

        return cls(
            layout=layout,
            kinds=tuple(kinds),
            notes=np.array(notes, dtype=np.int64),
            rows=np.array(rows, dtype=np.int64),
            full_levels=np.array(full_levels, dtype=np.float64),
        )

    def heard(self, hearing: SteadyHearing) -> HeardAtoms:
        """The atoms as a frame heard alone hears them, each on the channel it hears its note's proposal on.

        The atoms span the frame's bins at every count of atoms, so a dictionary of no atom is heard
        as no atom over the bins.
        """
        features = np.zeros((len(self.kinds), hearing.leak.shape[0]))
        caps = np.zeros(len(self.kinds))
        powers = np.zeros(len(self.kinds))
        for kind in sorted(set(self.kinds)):
            atoms = np.flatnonzero([atom_kind == kind for atom_kind in self.kinds])
            for place, positions in rows_by_place(hearing, kind, self.rows[atoms]):
                placed = atoms[positions]
                rows = [int(row) for row in self.rows[placed]]
                features[placed] = hearing.unit_features(place, rows)
                caps[placed] = self.full_levels[placed] * self.layout.gain(place)
                powers[placed] = [float(power.sum()) for power in hearing.steady_powers(place, rows)]

        return HeardAtoms(kinds=self.kinds, notes=self.notes, features=features, caps=caps, powers=powers)


@dataclass(frozen=True)
class NoteTrials:
    """Each proposed note's rows tried alone over what the frame holds before its rows sound.

    A row is heard on the channel the frame's hearing places its proposal on, and scored by the
    spectral term with the bins it falls short in counted at ``SHORTFALL_WEIGHT``. Every note's rows
    are scored in one batch.

    Attributes:
        fragment: The stem's frame.
        matcher: The candidate scoring machinery.
        hearing: How the frame hears each row.
    """

    fragment: Fragment
    matcher: FrameMatcher
    hearing: FrameHearing

    def proposed(self, catalog: KindCatalog, notes: List[int], *, doubled: bool) -> List[int]:
        """Each of ``notes`` on its best row, then, where ``doubled``, the first notes on a second duty cycle."""
        if not notes:
            return []

        rows_by_note = [catalog.rows_of(note) for note in notes]
        costs = split_by_group(self._costs(catalog.kind, np.concatenate(rows_by_note)), rows_by_note)
        chosen = [cheapest_row(rows, note_costs) for rows, note_costs in zip(rows_by_note, costs)]
        if not doubled:
            return chosen

        return [*chosen, *_second_duties(catalog, chosen, rows_by_note, costs)]

    def _costs(self, kind: GeneratorClassName, rows: np.ndarray) -> np.ndarray:
        """The cost of the frame with each of ``rows`` sounding alone beside what it holds before its rows sound."""
        powers = xp.asarray(self.hearing.leak + _proposal_powers(self.hearing, kind, rows))
        features = self.matcher.candidate_provider.features_of(powers)
        return self.matcher.scorer.shortfall_weighted_costs(self.fragment, features, SHORTFALL_WEIGHT)


def note_strengths(target: FitTarget, atoms: HeardAtoms, hearing: FrameHearing) -> NoteStrengths:
    """How strongly the frame sounds each note, every note fitted to it at once.

    The atoms are heard as a frame heard alone hears them (``NoteDictionary.heard``): each row at its
    channel's drive, as a note held through the whole window. They are fitted over what the frame
    holds before its rows sound, the leak of ``hearing``, from ``FREE_FIT_START`` for
    ``FREE_FIT_UPDATES`` updates. Among the frame's neighbors the fit hears each row alone as well,
    since the window model reads a note cut at a frame boundary approximately, and the fit weighs
    every note of the frame through what it reads.
    """
    levels = fitted_levels(
        target,
        atoms.features,
        atoms.caps,
        base=hearing.leak_features,
        start=FREE_FIT_START,
        updates=FREE_FIT_UPDATES,
    )
    return atoms.strengths(levels)


def proposed_rows(
    fragment: Fragment,
    target: FitTarget,
    layout: StemLayout,
    atoms: HeardAtoms,
    catalogs: Mapping[GeneratorClassName, KindCatalog],
    matcher: FrameMatcher,
    hearing: FrameHearing,
) -> Dict[GeneratorClassName, List[int]]:
    """The rows a frame's search starts from: each kind's strongest notes, each on its best row alone.

    Every note is fitted to the frame at once, its ``atoms`` heard alone over what ``hearing`` holds
    before its rows sound (``note_strengths``), and each kind proposes its ``PROPOSED_NOTES``
    strongest notes. A note is proposed on the row of its own, of any timbre and volume, that fits
    the frame best alone, which settles its duty cycle and a first volume. A row alone leaves the
    frame's other notes uncovered, so the bins it falls short in count at ``SHORTFALL_WEIGHT`` of
    their cost, and what it adds beyond the frame counts in full.

    Where the stem holds two pulses, its ``DOUBLED_NOTES`` strongest pulse notes are proposed again,
    each on the best row of a duty cycle sounding unlike its first, so two pulses may sound one note.

    Returns:
        The proposed rows of each kind the stem plays: its notes' rows, strongest first, then the
        second duty cycles in the same order.
    """
    strengths = note_strengths(target, atoms, hearing)
    trials = NoteTrials(fragment=fragment, matcher=matcher, hearing=hearing)
    proposals: Dict[GeneratorClassName, List[int]] = {}
    for kind in sorted(layout.kinds):
        notes = strengths.strongest(kind, PROPOSED_NOTES[kind])
        doubled = kind == GeneratorClassName.PULSE_GENERATOR and len(layout.of_kind(kind)) > 1
        proposals[kind] = trials.proposed(catalogs[kind], notes, doubled=doubled)

    return proposals


def _second_duties(
    catalog: KindCatalog, chosen: List[int], rows_by_note: List[np.ndarray], costs: List[np.ndarray]
) -> List[int]:
    """The first ``DOUBLED_NOTES`` notes on the best row of a duty cycle sounding unlike the one each was chosen on.

    A note held only in duty cycles sounding alike to its chosen one has no second duty cycle.
    """
    seconds: List[int] = []
    for row, rows, note_costs in list(zip(chosen, rows_by_note, costs))[:DOUBLED_NOTES]:
        alike = alike_timbres(int(catalog.timbres[row]))
        unlike = np.array([int(timbre) not in alike for timbre in catalog.timbres[rows]])
        if unlike.any():
            seconds.append(cheapest_row(rows[unlike], note_costs[unlike]))

    return seconds


def _proposal_powers(hearing: FrameHearing, kind: GeneratorClassName, rows: np.ndarray) -> np.ndarray:
    """What each row of ``kind`` adds to the frame, on the channel ``hearing`` places its proposal on.

    The rows placed on one channel are heard together.
    """
    heard = np.zeros((rows.shape[0], hearing.leak.shape[0]))
    for place, positions in rows_by_place(hearing, kind, rows):
        heard[positions] = hearing.powers(place, [int(row) for row in rows[positions]])

    return heard
