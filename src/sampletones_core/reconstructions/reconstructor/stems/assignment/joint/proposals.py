from dataclasses import dataclass
from typing import Dict, Final, List, Mapping, Self, Tuple

import numpy as np

from sampletones_core.constants.enums import GeneratorClassName
from sampletones_core.fft import Fragment
from sampletones_core.reconstructions.reconstructor.matching import FrameMatcher
from sampletones_shared.array import xp

from .catalog import FULL_VOLUME, KindCatalog, alike_timbres, strongest_rows
from .fit import FitTarget, fitted_levels
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


@dataclass(frozen=True)
class NoteDictionary:
    """One atom per note and timbre a stem's channels may sound, which a frame's levels are fitted over.

    An atom is the loudest row of its note in its timbre, so a level of one sounds that row, and it
    may reach as high as every channel of its kind playing it at full volume at the drive the stem
    gives each.

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
            reach = sum(1.0 / slot.drive**2 for slot in layout.of_kind(kind))
            sounded = sorted({int(note) for note in catalog.notes if note >= 0})
            for note, rows in strongest_rows(catalog, sounded).items():
                for row in rows:
                    kinds.append(kind)
                    notes.append(note)
                    features.append(catalog.features[row])
                    caps.append(reach * (FULL_VOLUME / max(int(catalog.volumes[row]), 1)) ** 2)
                    powers.append(float(catalog.powers[row].sum()))

        return cls(
            kinds=tuple(kinds),
            notes=np.array(notes, dtype=np.int64),
            features=np.stack(features) if features else np.zeros((0, 0)),
            caps=np.array(caps),
            powers=np.array(powers),
        )


def proposed_rows(
    fragment: Fragment,
    target: FitTarget,
    layout: StemLayout,
    dictionary: NoteDictionary,
    catalogs: Mapping[GeneratorClassName, KindCatalog],
    matcher: FrameMatcher,
) -> Dict[GeneratorClassName, List[int]]:
    """The rows a frame's search starts from: the strongest notes of each kind, each on its best row.

    The notes are the ones sounding strongest when every note is fitted to the frame at once, their
    strength the power each is fitted to sound, unweighted, so a bass counts for what it plays where
    the criterion's weights are light. A pulse or noise note is then proposed on the row of its own
    that fits the frame best alone with what it falls short of counted lightly, which settles its
    duty cycle and a first volume. With two pulses, the two strongest pulse notes are proposed on a
    second duty cycle too, so two pulses may sound one note.

    Returns:
        The proposed rows of each kind the stem plays, strongest note first.
    """
    levels = fitted_levels(
        target,
        dictionary.features,
        dictionary.caps,
        start=FREE_FIT_START,
        updates=FREE_FIT_UPDATES,
    )
    strengths: Dict[Tuple[GeneratorClassName, int], float] = {}
    for kind, note, energy in zip(dictionary.kinds, dictionary.notes, levels * dictionary.powers):
        key = (kind, int(note))
        strengths[key] = strengths.get(key, 0.0) + float(energy)

    proposals: Dict[GeneratorClassName, List[int]] = {}
    for kind in sorted(layout.kinds):
        notes = [
            note for note in _ranked_notes(strengths, kind)[: PROPOSED_NOTES[kind]] if strengths[(kind, note)] > 0.0
        ]
        proposals[kind] = _note_rows(fragment, catalogs[kind], notes, layout, kind, matcher)

    return proposals


def _ranked_notes(strengths: Mapping[Tuple[GeneratorClassName, int], float], kind: GeneratorClassName) -> List[int]:
    """The notes of ``kind``, the strongest first."""
    return sorted((note for key_kind, note in strengths if key_kind == kind), key=lambda note: -strengths[(kind, note)])


def _note_rows(
    fragment: Fragment,
    catalog: KindCatalog,
    notes: List[int],
    layout: StemLayout,
    kind: GeneratorClassName,
    matcher: FrameMatcher,
) -> List[int]:
    """Each note's best row alone, and a second duty cycle for the strongest pulse notes where two pulses play."""
    if not notes:
        return []

    drive = layout.of_kind(kind)[0].drive
    rows_by_note = [catalog.rows_of(note) for note in notes]
    stacked = np.concatenate(rows_by_note)
    powers = xp.asarray(catalog.powers[stacked] / drive**2)
    costs = matcher.scorer.shortfall_weighted_costs(
        fragment, matcher.candidate_provider.features_of(powers), SHORTFALL_WEIGHT
    )
    bounds = np.cumsum([0, *[len(rows) for rows in rows_by_note]])
    chosen: List[int] = []
    ranked: List[Tuple[np.ndarray, np.ndarray]] = []
    for index, rows in enumerate(rows_by_note):
        note_costs = costs[bounds[index] : bounds[index + 1]]
        chosen.append(int(rows[int(np.argmin(note_costs))]))
        ranked.append((rows, note_costs))

    if kind == GeneratorClassName.PULSE_GENERATOR and len(layout.of_kind(kind)) > 1:
        for row, (rows, note_costs) in list(zip(chosen, ranked))[:DOUBLED_NOTES]:
            taken = int(catalog.timbres[row])
            alike = alike_timbres(taken)
            unlike = np.array([int(timbre) not in alike for timbre in catalog.timbres[rows]])
            if unlike.any():
                chosen.append(int(rows[unlike][int(np.argmin(note_costs[unlike]))]))

    return chosen
