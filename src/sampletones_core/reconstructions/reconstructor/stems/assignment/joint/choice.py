from dataclasses import dataclass
from typing import Dict, Final, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from sampletones_core.constants.enums import GeneratorClassName
from sampletones_core.fft import Fragment
from sampletones_core.reconstructions.reconstructor.contribution import Contribution
from sampletones_core.reconstructions.reconstructor.matching import FrameMatcher
from sampletones_core.reconstructions.reconstructor.mix import FrameMix

from .catalog import KindCatalog, alike_timbres
from .combinations import CombinationSearch, Rows
from .layout import StemLayout

FINALISTS: Final[int] = 6
TIMBRE_TOLERANCE: Final[float] = 0.02
LEVEL_STEPS: Final[int] = 2


@dataclass(frozen=True)
class ScoredCombination:
    """A combination with the full cost of the frame it sounds, and what each of its channels adds.

    Attributes:
        rows: The row each of the stem's channels plays, in the layout's channel order.
        cost: The full criterion of the frame with the rows sounding together.
        contributions: What each channel adds to the frame, ``None`` for a silent one.
    """

    rows: Rows
    cost: float
    contributions: Tuple[Optional[Contribution], ...]


class CombinationJudge:
    """Scores combinations with the full criterion, which reads their waveforms as well as their powers.

    Each sounding channel is phased in turn, loudest first, against what the louder ones leave of
    the frame's waveform, at the drive the stem gives it, and the frame is then scored with all of
    them sounding, exactly as a column scores one candidate beside a mix. A channel phased once
    behind the same louder rows keeps its phase for every combination of the frame sharing them.
    """

    def __init__(
        self,
        fragment: Fragment,
        layout: StemLayout,
        catalogs: Mapping[GeneratorClassName, KindCatalog],
        matcher: FrameMatcher,
        weights: np.ndarray,
    ) -> None:
        self.fragment = fragment
        self.layout = layout
        self.catalogs = catalogs
        self.matcher = matcher
        self.weights = weights
        self._phased: Dict[Tuple[Tuple[int, int], ...], Contribution] = {}

    def scored(self, combinations: Sequence[Rows]) -> List[ScoredCombination]:
        """The full cost of the frame with each combination's rows sounding together, scored in one pass."""
        built = [self._contributions(rows) for rows in combinations]
        costs = self.matcher.mix_costs(self.fragment, [mix for _, mix in built])
        return [
            ScoredCombination(rows=rows, cost=float(cost), contributions=contributions)
            for rows, (contributions, _), cost in zip(combinations, built, costs)
        ]

    def _contributions(self, rows: Rows) -> Tuple[Tuple[Optional[Contribution], ...], FrameMix]:
        """What each of ``rows`` adds to the frame, phased loudest first, and the mix they sound."""
        loudness = [
            float(self.catalogs[slot.kind].features[row] @ self.weights) / slot.drive**2
            for slot, row in zip(self.layout.slots, rows)
        ]
        contributions: List[Optional[Contribution]] = [None] * len(rows)
        mix = FrameMix.empty(self.fragment)
        phased: Tuple[Tuple[int, int], ...] = ()
        for index in sorted(range(len(rows)), key=lambda position: -loudness[position]):
            slot, row = self.layout.slots[index], rows[index]
            catalog = self.catalogs[slot.kind]
            if not catalog.sounding(row):
                continue
            phased = (*phased, (index, row))
            contribution = self._phased.get(phased)
            if contribution is None:
                contribution = self.matcher.contribution(
                    catalog.instructions[row],
                    mix.residual_waveform(self.fragment),
                    catalog.powers[row] / slot.drive**2,
                    drive=slot.drive,
                )
                self._phased[phased] = contribution
            contributions[index] = contribution
            mix = mix.added(contribution)

        return tuple(contributions), mix

    def best(self, search: CombinationSearch, candidates: Sequence[Rows]) -> ScoredCombination:
        """The cheapest of ``candidates`` under the full criterion, thinned and with its pulses' duty cycles settled.

        The spectral ranking that orders the candidates favors a quiet extra channel that fills a
        little of the frame's power, which the full criterion can charge more for than it gains, so
        the winner silences its channels one at a time for as long as the full criterion falls, a
        channel left then also tried at the volumes taking up what the silenced one played.

        Two duty cycles a pulse note sounds alike in are told apart by the waveform, so a pulse is
        tried on the duty cycle sharing its spectrum and on every other duty cycle of its note and
        volume whose spectral cost stays within ``TIMBRE_TOLERANCE`` of its own, and keeps the one the
        full criterion prefers.
        """
        winner = _cheapest(self.scored(candidates[:FINALISTS]))
        winner = self._thinned(search, self._timbres_settled(search, winner))
        return self._timbres_settled(search, winner)

    def _thinned(self, search: CombinationSearch, winner: ScoredCombination) -> ScoredCombination:
        """``winner`` with the channels silenced whose silence the full criterion prefers, one at a time."""
        while True:
            silenced = [
                _replaced(winner.rows, index, self.catalogs[slot.kind].silence)
                for index, slot in enumerate(self.layout.slots)
                if self.catalogs[slot.kind].sounding(winner.rows[index])
            ]
            if not silenced:
                return winner

            trials = list(dict.fromkeys([*silenced, *self._releveled(search, silenced)]))
            trimmed = _cheapest(self.scored(trials))
            if trimmed.cost >= winner.cost:
                return winner

            winner = trimmed

    def _releveled(self, search: CombinationSearch, combinations: Sequence[Rows]) -> List[Rows]:
        """Each combination with one of its sounding pulses or noise at the volumes taking up the frame's power.

        A channel takes the volume of its note and timbre that the spectral term prefers with the
        rest of its combination sounding, and is offered a step either side as well, since the
        spectral term reads a level more loosely than the waveform does.
        """
        moves: List[Tuple[Rows, int, np.ndarray]] = []
        for rows in combinations:
            for index, slot in enumerate(self.layout.slots):
                catalog = self.catalogs[slot.kind]
                if slot.kind != GeneratorClassName.TRIANGLE_GENERATOR and catalog.sounding(rows[index]):
                    note, timbre = int(catalog.notes[rows[index]]), int(catalog.timbres[rows[index]])
                    moves.append((rows, index, catalog.rows_in(note, timbre)))

        if not moves:
            return []

        costs = search.spectral_costs(
            [_replaced(rows, index, int(option)) for rows, index, options in moves for option in options]
        )
        releveled: List[Rows] = []
        start = 0
        for rows, index, options in moves:
            chosen = int(options[int(np.argmin(costs[start : start + len(options)]))])
            start += len(options)
            catalog = self.catalogs[self.layout.slots[index].kind]
            releveled.extend(_replaced(rows, index, row) for row in [chosen, *catalog.neighbors(chosen, LEVEL_STEPS)])

        return releveled

    def _timbres_settled(self, search: CombinationSearch, winner: ScoredCombination) -> ScoredCombination:
        """``winner`` with one pulse on the other duty cycle of its note and volume the full criterion prefers."""
        trials: List[Rows] = []
        alike: List[bool] = []
        for index, slot in enumerate(self.layout.slots):
            catalog = self.catalogs[slot.kind]
            row = winner.rows[index]
            if slot.kind != GeneratorClassName.PULSE_GENERATOR or not catalog.sounding(row):
                continue

            shared = alike_timbres(int(catalog.timbres[row]))
            for other in catalog.rows_of(int(catalog.notes[row])):
                if catalog.volumes[other] == catalog.volumes[row] and int(other) != row:
                    trials.append(_replaced(winner.rows, index, int(other)))
                    alike.append(int(catalog.timbres[other]) in shared)

        if not trials:
            return winner

        spectral = search.spectral_costs([winner.rows, *trials])
        kept = [
            trial
            for trial, shares, cost in zip(trials, alike, spectral[1:])
            if shares or abs(float(cost) - float(spectral[0])) <= TIMBRE_TOLERANCE
        ]
        if not kept:
            return winner

        return _cheapest([winner, *self.scored(kept)])


def _replaced(rows: Rows, index: int, row: int) -> Rows:
    """``rows`` with channel ``index`` playing ``row``."""
    return tuple(row if position == index else kept for position, kept in enumerate(rows))


def _cheapest(combinations: Sequence[ScoredCombination]) -> ScoredCombination:
    """The combination of the lowest full cost, the first of equal ones."""
    return min(combinations, key=lambda combination: combination.cost)
