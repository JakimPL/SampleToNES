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
from .hearing import FrameHearing
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

    A note's strength is the power its atoms are fitted to sound, summed over its timbres and
    unweighted, so a bass counts for what it plays where the criterion's weights are light.

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
class NoteDictionary:
    """One atom per note and timbre a stem's channels may sound, which a frame's levels are fitted over.

    An atom is the unit row of its note in its timbre, at unit drive, so a level of one sounds that
    row on a channel driven at one. Its cap is what every channel of its kind playing it at full
    volume sounds, each at the drive the stem gives it. The atoms stand kind by kind in name order,
    each kind's notes ascending and each note's timbres ascending.

    Attributes:
        kinds: Each atom's kind.
        notes: Each atom's note.
        features: Each atom's feature values, one per row.
        caps: The highest level each atom may reach.
        powers: Each atom's whole power, which a fitted note's strength is read in.
    """

    kinds: Tuple[GeneratorClassName, ...]
    notes: np.ndarray
    features: np.ndarray
    caps: np.ndarray
    powers: np.ndarray

    @classmethod
    def of(cls, layout: StemLayout, catalogs: Mapping[GeneratorClassName, KindCatalog]) -> Self:
        """The dictionary of every note ``layout``'s channels may sound."""
        kinds: List[GeneratorClassName] = []
        notes: List[int] = []
        features: List[np.ndarray] = []
        caps: List[float] = []
        powers: List[float] = []
        for kind in sorted(layout.kinds):
            catalog = catalogs[kind]
            gain = layout.gain(kind)
            for note in catalog.sounded_notes:
                for unit in catalog.units_of(note):
                    kinds.append(kind)
                    notes.append(note)
                    features.append(catalog.features[unit.row])
                    caps.append(gain * unit.full_level)
                    powers.append(float(catalog.powers[unit.row].sum()))

        return cls(
            kinds=tuple(kinds),
            notes=np.array(notes, dtype=np.int64),
            features=np.stack(features) if features else np.zeros((0, 0)),
            caps=np.array(caps),
            powers=np.array(powers),
        )

    def strengths(self, levels: np.ndarray) -> NoteStrengths:
        """How strongly the frame sounds each note, the atoms fitted at ``levels``."""
        strengths: Dict[KindNote, float] = {}
        for kind, note, energy in zip(self.kinds, self.notes, levels * self.powers):
            key = (kind, int(note))
            strengths[key] = strengths.get(key, 0.0) + float(energy)

        return NoteStrengths(strengths=strengths)


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


def proposed_rows(
    fragment: Fragment,
    target: FitTarget,
    layout: StemLayout,
    dictionary: NoteDictionary,
    catalogs: Mapping[GeneratorClassName, KindCatalog],
    matcher: FrameMatcher,
    hearing: FrameHearing,
) -> Dict[GeneratorClassName, List[int]]:
    """The rows a frame's search starts from: each kind's strongest notes, each on its best row alone.

    Every note is fitted to the frame at once, over what the frame holds before its rows sound, from
    ``FREE_FIT_START`` for ``FREE_FIT_UPDATES`` updates. Each kind proposes its ``PROPOSED_NOTES``
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
    levels = fitted_levels(
        target,
        dictionary.features,
        dictionary.caps,
        base=hearing.leak_features,
        start=FREE_FIT_START,
        updates=FREE_FIT_UPDATES,
    )
    strengths = dictionary.strengths(levels)
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
    places = np.array([hearing.place_of(kind, int(row)) for row in rows])
    heard = np.zeros((rows.shape[0], hearing.leak.shape[0]))
    for place in np.unique(places):
        chosen = places == place
        heard[chosen] = hearing.powers(int(place), [int(row) for row in rows[chosen]])

    return heard
