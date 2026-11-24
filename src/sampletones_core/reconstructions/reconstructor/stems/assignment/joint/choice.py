import itertools
from dataclasses import dataclass
from typing import Dict, Final, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from sampletones_core.constants.enums import GeneratorClassName
from sampletones_core.fft import Fragment
from sampletones_core.reconstructions.reconstructor.contribution import Contribution
from sampletones_core.reconstructions.reconstructor.matching import FrameMatcher
from sampletones_core.reconstructions.reconstructor.mix import FrameMix

from .batches import cheapest_row, split_by_group
from .catalog import KindCatalog, alike_timbres
from .combinations import CombinationSearch, Rows
from .continuity import StemContinuity
from .hearing import DrivenFeatures, FrameHearing
from .layout import StemLayout

FINALISTS: Final[int] = 6
TIMBRE_TOLERANCE: Final[float] = 0.02
LEVEL_STEPS: Final[int] = 2

Phasing = Tuple[Tuple[int, int], ...]
Contributions = Tuple[Optional[Contribution], ...]


@dataclass(frozen=True)
class ScoredCombination:
    """A combination with the full cost of the frame it sounds, and what each of its channels adds.

    Attributes:
        rows: The row each of the stem's channels plays, in the layout's channel order.
        cost: The full criterion of the frame with the rows sounding together.
        contributions: What each channel adds to the frame, ``None`` for a silent one.
        charge: What the frame's choice pays for the combination breaking with the frames beside it.
    """

    rows: Rows
    cost: float
    contributions: Contributions
    charge: float

    @property
    def weighed(self) -> float:
        """What the frame's choice and the decoders weigh the combination by: its full cost and its charge."""
        return self.cost + self.charge


@dataclass(frozen=True)
class DutyTrial:
    """A combination with one pulse moved to another duty cycle of its note and volume.

    Attributes:
        rows: The combination with the pulse moved.
        shares_spectrum: Whether the new duty cycle sounds the same spectrum as the pulse's own.
    """

    rows: Rows
    shares_spectrum: bool

    def left_to_waveform(self, spectral_cost: float, own_cost: float) -> bool:
        """Whether the spectral term leaves the waveform to tell this duty cycle from the pulse's own.

        It does where the two share a spectrum, and where the trial's spectral cost lies within
        ``TIMBRE_TOLERANCE`` of the cost of the pulse's own duty cycle, ``own_cost``.
        """
        return self.shares_spectrum or abs(spectral_cost - own_cost) <= TIMBRE_TOLERANCE


@dataclass(frozen=True)
class Releveling:
    """One sounding pulse or noise of a combination, with the rows of its note and timbre it may move to.

    Attributes:
        rows: The combination.
        place: The channel's place in the layout.
        options: Every row of the channel's note and timbre, in catalog order.
    """

    rows: Rows
    place: int
    options: np.ndarray

    def moved(self, row: int) -> Rows:
        """The combination with the channel playing ``row``."""
        return _replaced(self.rows, self.place, row)


class CombinationJudge:
    """Chooses a stem's combination in one frame with the full criterion, which reads waveforms as well as powers.

    The search ranks combinations by the spectral term, and the judge decides among the cheapest:

    1. **Scoring.** Each sounding channel is phased in turn, loudest first by the criterion's
       weighting of its row heard alone at the drive the stem gives it (``DrivenFeatures``), against
       what the louder ones leave of the frame's waveform, since the louder channels shape that
       residual most. The frame is then scored with all of them sounding, exactly as a column scores
       one candidate beside a mix. A channel phased once behind the same louder rows keeps its phase
       for every combination of the frame sharing them. A combination is weighed by its cost and the
       charge it pays for breaking with the frames beside it.
    2. **Finalists.** The ``FINALISTS`` cheapest by the spectral ranking, and, where the charge binds,
       the combinations the neighbors play, so the frame may hold through what they play.
    3. **The choice.** The finalist weighed lowest, its pulses' duty cycles settled, then thinned,
       then its duty cycles settled again (``best``).
    4. **The pool.** The combinations a decoder over whole combinations chooses among (``pooled``).

    Of combinations weighed alike, the earlier stands.
    """

    def __init__(
        self,
        fragment: Fragment,
        layout: StemLayout,
        catalogs: Mapping[GeneratorClassName, KindCatalog],
        matcher: FrameMatcher,
        weights: np.ndarray,
        driven: DrivenFeatures,
        hearing: FrameHearing,
        continuity: StemContinuity,
    ) -> None:
        self.fragment = fragment
        self.layout = layout
        self.catalogs = catalogs
        self.matcher = matcher
        self.weights = weights
        self.driven = driven
        self.hearing = hearing
        self.continuity = continuity
        self._phasings: Dict[Phasing, Contribution] = {}

    def scored(self, combinations: Sequence[Rows]) -> List[ScoredCombination]:
        """The full cost of the frame with each combination's rows sounding together, scored in one pass."""
        built = [self._contributions(rows) for rows in combinations]
        costs = self.matcher.mix_costs(self.fragment, [mix for _, mix in built])
        return [
            ScoredCombination(
                rows=rows,
                cost=float(cost),
                contributions=contributions,
                charge=self.continuity.charge(rows),
            )
            for rows, (contributions, _), cost in zip(combinations, built, costs)
        ]

    def finalists(self, candidates: Sequence[Rows]) -> List[ScoredCombination]:
        """The first ``FINALISTS`` of ``candidates``, the spectral ranking's cheapest, under the full criterion.

        Where the frame's choice keeps to the frames beside it, the combinations they play join the
        finalists, so the frame may hold through what its neighbors play.
        """
        cheapest = list(candidates[:FINALISTS])
        held = [rows for rows in self.continuity.beside() if rows not in cheapest]
        return self.scored([*cheapest, *held])

    def best(self, search: CombinationSearch, finalists: Sequence[ScoredCombination]) -> ScoredCombination:
        """The finalist weighed lowest, thinned and with its pulses' duty cycles settled.

        The spectral ranking that orders the candidates favors a quiet extra channel that fills a
        little of the frame's power, which the full criterion can charge more for than it gains, so
        the winner is thinned (``_thinned``). The spectral term hears two duty cycles of a note alike
        where they share a spectrum, so the waveform settles them (``_timbres_settled``), before the
        thinning and again after it.
        """
        winner = _cheapest(finalists)
        winner = self._thinned(search, self._timbres_settled(search, winner))
        return self._timbres_settled(search, winner)

    def pooled(
        self,
        search: CombinationSearch,
        finalists: Sequence[ScoredCombination],
        winner: ScoredCombination,
        previous: Optional[Rows],
    ) -> List[ScoredCombination]:
        """The combinations a decoder over whole combinations chooses among in the frame, the winner first.

        The pool holds the winner with every set of its sounding channels silenced, so a path can let
        any of its channels fall silent together where the frames around ask for it, as decoders of one
        channel at a time can. It holds the finalists, each also with one of its channels silenced, and
        the previous frame's winner, so a path can hold the combination the frame before sounded through
        a change. Every combination is scored under the full criterion and reads once, whatever order
        its pulses stand in, as it was first pooled: the winner, then the finalists, then the others.

        Args:
            search: The frame's combination search, which knows the stem's interchangeable pulses.
            finalists: The frame's finalists, scored.
            winner: The combination the frame's search chose.
            previous: The combination the stem's previous frame chose, or ``None`` after a rest.

        Returns:
            The pooled combinations, each once.
        """
        pool: Dict[Rows, ScoredCombination] = {}
        for combination in [winner, *finalists]:
            pool.setdefault(search.canonical(combination.rows), combination)

        fresh = self._unpooled(search, self._variations(finalists, winner, previous), pool)
        if fresh:
            pool.update((combination.rows, combination) for combination in self.scored(fresh))

        return list(pool.values())

    def _contributions(self, rows: Rows) -> Tuple[Contributions, FrameMix]:
        """What each of ``rows`` adds to the frame, phased loudest first, and the mix they sound together."""
        contributions: List[Optional[Contribution]] = [None] * len(rows)
        mix = self.hearing.empty_mix(self.fragment)
        louder: Phasing = ()
        for index in self._loudest_first(rows):
            louder = (*louder, (index, rows[index]))
            contribution = self._phased(louder, mix)
            contributions[index] = contribution
            mix = mix.added(contribution)

        return tuple(contributions), mix

    def _loudest_first(self, rows: Rows) -> List[int]:
        """The places of the channels ``rows`` sounds, loudest first by the criterion's weighting.

        Of channels equally loud, the earlier in the layout comes first.
        """
        loudness = {index: self._loudness(index, rows[index]) for index in self._sounding(rows)}
        return sorted(loudness, key=loudness.__getitem__, reverse=True)

    def _loudness(self, index: int, row: int) -> float:
        """How loud the channel at ``index`` plays ``row`` at its drive, as the criterion weighs the bins.

        It is the weighted feature values of the row heard alone on the channel, its steady loudness
        at the drive: the phasing works on the frame's own samples, which sound each channel's row at
        its drive whatever the analysis window reads of the neighbors.
        """
        return float(self.driven.at(self.layout.slots[index], [row])[0] @ self.weights)

    def _phased(self, phasing: Phasing, mix: FrameMix) -> Contribution:
        """What the last channel of ``phasing`` adds, phased against what ``mix`` leaves of the frame's waveform.

        The channels before it in ``phasing``, with their rows, make ``mix`` what it is, so a
        contribution phased once serves every combination of the frame sharing them.
        """
        cached = self._phasings.get(phasing)
        if cached is not None:
            return cached

        index, row = phasing[-1]
        slot = self.layout.slots[index]
        contribution = self.matcher.contribution(
            self.catalogs[slot.kind].instructions[row],
            mix.residual_waveform(self.fragment),
            self.hearing.powers(index, [row])[0],
            drive=slot.drive,
        )
        self._phasings[phasing] = contribution
        return contribution

    def _thinned(self, search: CombinationSearch, winner: ScoredCombination) -> ScoredCombination:
        """``winner`` with channels silenced one at a time, for as long as a silence lowers what it weighs.

        Each round tries the winner with each of its sounding channels silenced, and each of those
        with a pulse or noise left at the volumes taking up what the silenced channel played
        (``_releveled``). The cheapest trial replaces the winner where it weighs strictly less.
        """
        while True:
            silenced = self._each_silenced(winner.rows)
            if not silenced:
                return winner

            trials = list(dict.fromkeys([*silenced, *self._releveled(search, silenced)]))
            trimmed = _cheapest(self.scored(trials))
            if trimmed.weighed >= winner.weighed:
                return winner

            winner = trimmed

    def _releveled(self, search: CombinationSearch, combinations: Sequence[Rows]) -> List[Rows]:
        """Each combination with one of its sounding pulses or noise at the volumes taking up the frame's power.

        A channel takes the volume of its note and timbre that the spectral term prefers with the rest
        of its combination sounding, the earlier of equally cheap ones, and is offered its
        ``LEVEL_STEPS`` nearest volumes as well, since the spectral term reads a level more loosely
        than the waveform does. Every channel's volumes are scored in one batch.
        """
        movable = [moving for rows in combinations for moving in self._levelings(rows)]
        if not movable:
            return []

        costs = search.spectral_costs([moving.moved(int(option)) for moving in movable for option in moving.options])
        releveled: List[Rows] = []
        for moving, option_costs in zip(movable, split_by_group(costs, [moving.options for moving in movable])):
            chosen = cheapest_row(moving.options, option_costs)
            catalog = self.catalogs[self.layout.slots[moving.place].kind]
            releveled.extend(moving.moved(row) for row in [chosen, *catalog.neighbors(chosen, LEVEL_STEPS)])

        return releveled

    def _levelings(self, rows: Rows) -> List[Releveling]:
        """Every sounding channel of ``rows`` playing more than one level, with the rows of its note and timbre."""
        levelings: List[Releveling] = []
        for index, slot in enumerate(self.layout.slots):
            catalog = self.catalogs[slot.kind]
            if slot.plays_levels and catalog.sounding(rows[index]):
                levelings.append(Releveling(rows=rows, place=index, options=catalog.rows_like(rows[index])))

        return levelings

    def _timbres_settled(self, search: CombinationSearch, winner: ScoredCombination) -> ScoredCombination:
        """``winner``, or the winner with one pulse on another duty cycle of its note and volume, as it weighs least.

        The duty cycles tried are those the spectral term leaves to the waveform to tell apart
        (``_told_apart_by_waveform``). Of equal weights, the winner stands.
        """
        trials = self._duty_trials(winner.rows)
        if not trials:
            return winner

        kept = self._told_apart_by_waveform(search, winner.rows, trials)
        if not kept:
            return winner

        return _cheapest([winner, *self.scored(kept)])

    def _duty_trials(self, rows: Rows) -> List[DutyTrial]:
        """Each sounding pulse of ``rows`` moved to every other duty cycle of its note and volume."""
        trials: List[DutyTrial] = []
        for index, slot in enumerate(self.layout.slots):
            catalog = self.catalogs[slot.kind]
            row = rows[index]
            if slot.kind != GeneratorClassName.PULSE_GENERATOR or not catalog.sounding(row):
                continue

            shared = alike_timbres(int(catalog.timbres[row]))
            for other in _other_duty_cycles(catalog, row):
                trials.append(
                    DutyTrial(rows=_replaced(rows, index, other), shares_spectrum=int(catalog.timbres[other]) in shared)
                )

        return trials

    @staticmethod
    def _told_apart_by_waveform(search: CombinationSearch, rows: Rows, trials: Sequence[DutyTrial]) -> List[Rows]:
        """The duty trials the spectrum leaves to the waveform to tell from ``rows``, in trial order."""
        spectral = search.spectral_costs([rows, *(trial.rows for trial in trials)])
        own_cost = float(spectral[0])
        return [
            trial.rows for trial, cost in zip(trials, spectral[1:]) if trial.left_to_waveform(float(cost), own_cost)
        ]

    def _variations(
        self, finalists: Sequence[ScoredCombination], winner: ScoredCombination, previous: Optional[Rows]
    ) -> List[Rows]:
        """The combinations a path may take beside the scored ones.

        These are the winner with every set of its channels silenced, each finalist with one channel
        silenced, and the previous frame's winner.
        """
        variations = self._every_set_silenced(winner.rows)
        for combination in finalists:
            variations.extend(self._each_silenced(combination.rows))

        if previous is not None:
            variations.append(previous)

        return variations

    @staticmethod
    def _unpooled(
        search: CombinationSearch, trials: Sequence[Rows], pool: Mapping[Rows, ScoredCombination]
    ) -> List[Rows]:
        """``trials`` in the order of their pulses that reads once, each once, leaving those ``pool`` already holds."""
        return list(dict.fromkeys(rows for rows in map(search.canonical, trials) if rows not in pool))

    def _sounding(self, rows: Rows) -> List[int]:
        """The places of the channels ``rows`` sounds, in the layout's order."""
        return [index for index, slot in enumerate(self.layout.slots) if self.catalogs[slot.kind].sounding(rows[index])]

    def _each_silenced(self, rows: Rows) -> List[Rows]:
        """``rows`` with each of its sounding channels silenced in turn, in the layout's order."""
        return [self._silent_at(rows, [index]) for index in self._sounding(rows)]

    def _every_set_silenced(self, rows: Rows) -> List[Rows]:
        """``rows`` with every set of its sounding channels silenced, smaller sets first."""
        sounding = self._sounding(rows)
        silenced: List[Rows] = []
        for count in range(1, len(sounding) + 1):
            for places in itertools.combinations(sounding, count):
                silenced.append(self._silent_at(rows, places))

        return silenced

    def _silent_at(self, rows: Rows, places: Sequence[int]) -> Rows:
        """``rows`` with the channels at ``places`` silenced."""
        silent = rows
        for index in places:
            silent = _replaced(silent, index, self.catalogs[self.layout.slots[index].kind].silence)

        return silent


def _other_duty_cycles(catalog: KindCatalog, row: int) -> List[int]:
    """The rows of ``row``'s note at its volume in every other duty cycle, in catalog order."""
    return [
        int(other)
        for other in catalog.rows_of(int(catalog.notes[row]))
        if catalog.volumes[other] == catalog.volumes[row] and int(other) != row
    ]


def _replaced(rows: Rows, index: int, row: int) -> Rows:
    """``rows`` with channel ``index`` playing ``row``."""
    return tuple(row if position == index else kept for position, kept in enumerate(rows))


def _weight_of(combination: ScoredCombination) -> float:
    return combination.weighed


def _cheapest(combinations: Sequence[ScoredCombination]) -> ScoredCombination:
    """The combination the frame's choice weighs lowest, the first of equal ones."""
    return min(combinations, key=_weight_of)
