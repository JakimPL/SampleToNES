import itertools
from dataclasses import dataclass
from typing import Dict, Final, List, Mapping, Optional, Self, Sequence, Tuple

import numpy as np

from sampletones_core.constants.enums import GeneratorClassName
from sampletones_core.fft import Fragment
from sampletones_core.reconstructions.reconstructor.matching import FrameMatcher

from .batches import cheapest_row, split_by_group
from .catalog import KindCatalog, UnitRow
from .fit import FitTarget, fitted_combinations
from .hearing import FrameHearing
from .layout import StemLayout

FIRST_UPDATES: Final[int] = 5
FURTHER_UPDATES: Final[int] = 15
SURVIVORS: Final[int] = 160
SCANNED_COMBINATIONS: Final[int] = 72
DISTINCT_COMBINATIONS: Final[int] = 12
REFINEMENT_SWEEPS: Final[int] = 2
SILENT_ENTRY: Final[int] = 0

Rows = Tuple[int, ...]
Choice = Tuple[Optional[int], ...]


@dataclass(frozen=True)
class Combination:
    """One row for every channel of a stem, and the spectral cost of the frame they sound together.

    Attributes:
        rows: The row each of the stem's channels plays, in the layout's channel order; a silent
            channel plays its kind's silent row.
        cost: The spectral cost of the frame with the rows sounding together.
    """

    rows: Rows
    cost: float


def searched_choices(layout: StemLayout, proposals: Mapping[GeneratorClassName, Sequence[int]]) -> List[Choice]:
    """Every choice of proposals the stem may sound together: a proposal or silence on each of its channels.

    A kind sounds every set of its proposals up to as many as it has channels: none first, then each
    proposal alone, then every pair, each set in proposal order. A set's proposals go to the kind's
    channels in layout order, and the channels left over fall silent, so pulses driven alike sound
    each set once. The kinds' sets are crossed in kind name order, the first kind's sets varying
    slowest, and a choice is kept where it sounds at most the stem's count of channels.

    The search keeps this order among choices of equal cost: a kind's silence before its sets that
    sound, smaller sets before larger ones, and the stronger proposals first.

    Args:
        layout: The stem's channels.
        proposals: The rows proposed for each kind, strongest first.

    Returns:
        The choices, each one entry per channel in layout order, ``None`` for silence.
    """
    kinds = sorted(layout.kinds)
    sets = [_proposal_sets(proposals.get(kind, ()), len(layout.of_kind(kind))) for kind in kinds]
    choices = [_placed(layout, dict(zip(kinds, picked))) for picked in itertools.product(*sets)]
    return [choice for choice in choices if _sounding(choice) <= layout.cap]


def _proposal_sets(offered: Sequence[int], channels: int) -> List[Choice]:
    """Every set of ``offered`` up to ``channels`` large, smaller first, each padded with silence to ``channels``."""
    sets: List[Choice] = [(None,) * channels]
    for sounding in range(1, channels + 1):
        for picked in itertools.combinations([int(row) for row in offered], sounding):
            sets.append((*picked, *([None] * (channels - sounding))))

    return sets


def _placed(layout: StemLayout, picked: Mapping[GeneratorClassName, Choice]) -> Choice:
    """Each kind's ``picked`` set on the kind's channels, in layout order."""
    left = {kind: list(rows) for kind, rows in picked.items()}
    return tuple(left[slot.kind].pop(0) for slot in layout.slots)


def _sounding(choice: Choice) -> int:
    """How many channels ``choice`` sounds."""
    return sum(row is not None for row in choice)


@dataclass(frozen=True)
class ChannelUnits:
    """What one fitted channel may play across a frame's choices: its silence, or a proposal's unit at a level.

    A proposal's unit is the unit row of its note and timbre, heard as the frame's fit reads it on
    the channel, so a level of one sounds the unit row. The level starts at the proposal's own volume
    and rises at most to full volume. The channel's silence is ``SILENT_ENTRY``, a unit of no power
    held at level zero.

    Attributes:
        place: The channel's place in the layout.
        entries: Each choice's entry on the channel.
        units: The unit row of each proposal the channel may play, keyed by the proposal's row.
        features: Each entry's unit, in feature values.
        powers: Each entry's unit, in power.
        caps: Each entry's highest level.
        starts: Each entry's first level.
    """

    place: int
    entries: np.ndarray
    units: Dict[int, UnitRow]
    features: np.ndarray
    powers: np.ndarray
    caps: np.ndarray
    starts: np.ndarray

    @classmethod
    def of(cls, choices: Sequence[Choice], place: int, catalog: KindCatalog, hearing: FrameHearing, bins: int) -> Self:
        """The units of the channel at ``place`` across ``choices``, each proposal an entry in row order."""
        played = [choice[place] for choice in choices]
        offered = sorted({row for row in played if row is not None})
        units = [catalog.unit_of(row) for row in offered]
        entry_of = {row: entry for entry, row in enumerate(offered, start=SILENT_ENTRY + 1)}
        unit_rows = [unit.row for unit in units]
        silence = np.zeros((1, bins))
        return cls(
            place=place,
            entries=np.array([SILENT_ENTRY if row is None else entry_of[row] for row in played]),
            units=dict(zip(offered, units)),
            features=np.concatenate([silence, hearing.unit_features(place, unit_rows)]),
            powers=np.concatenate([silence, hearing.unit_powers(place, unit_rows)]),
            caps=np.array([0.0, *(unit.full_level for unit in units)]),
            starts=np.array([0.0, *(unit.level_of(catalog.sounding_volume(row)) for row, unit in zip(offered, units))]),
        )


@dataclass(frozen=True)
class ChoiceFits:
    """The fit of a frame's choices, one model per choice: its fixed part and each fitted channel's unit and cap.

    The fixed part is what the frame holds before its rows sound and the rows of the channels
    playing one level. A model sounds its fixed part and each fitted channel's unit at its level.

    Attributes:
        units: Each fitted channel's unit in every choice, in feature values.
        unit_powers: Each fitted channel's unit in every choice, in power.
        caps: Each fitted channel's highest level in every choice.
        base: Every choice's fixed part, in feature values.
        base_powers: Every choice's fixed part, in power.
    """

    units: List[np.ndarray]
    unit_powers: List[np.ndarray]
    caps: List[np.ndarray]
    base: np.ndarray
    base_powers: np.ndarray

    @classmethod
    def of(cls, channels: Sequence[ChannelUnits], base: np.ndarray, base_powers: np.ndarray) -> Self:
        """The fit of the choices ``channels`` hold the entries of, over their fixed parts."""
        return cls(
            units=[channel.features[channel.entries] for channel in channels],
            unit_powers=[channel.powers[channel.entries] for channel in channels],
            caps=[channel.caps[channel.entries] for channel in channels],
            base=base,
            base_powers=base_powers,
        )

    def kept(self, choices: np.ndarray) -> Self:
        """The fit of ``choices`` alone, in their order."""
        return type(self)(
            units=[unit[choices] for unit in self.units],
            unit_powers=[power[choices] for power in self.unit_powers],
            caps=[cap[choices] for cap in self.caps],
            base=self.base[choices],
            base_powers=self.base_powers[choices],
        )

    def fitted(self, target: FitTarget, levels: Sequence[np.ndarray], updates: int) -> List[np.ndarray]:
        """Every channel's levels after ``updates`` more updates from ``levels``."""
        return fitted_combinations(target, self.units, self.base, levels, self.caps, updates=updates)

    def powers(self, levels: Sequence[np.ndarray]) -> np.ndarray:
        """What every choice sounds at ``levels``, in power."""
        mixed = self.base_powers.copy()
        for unit, level in zip(self.unit_powers, levels):
            mixed = mixed + level[:, None] * unit

        return mixed


@dataclass(frozen=True)
class Survivors:
    """The choices the short fit ranks cheapest, after the longer fit.

    Attributes:
        choices: Each survivor's index among the choices, the cheapest of the short fit first.
        levels: Each fitted channel's level in every survivor.
        costs: Each survivor's spectral cost at its levels.
    """

    choices: np.ndarray
    levels: List[np.ndarray]
    costs: np.ndarray


class CombinationSearch:
    """Searches the combinations of a frame's proposals for the rows that fit the frame best together.

    A choice puts a proposal or silence on each of the stem's channels (``searched_choices``). Every
    choice is fitted to the frame at once: each pulse's and the noise's level scales the unit row of
    its proposal's note and timbre, and the triangle sounds its one level. The best fits move onto
    the library's rows nearest their levels, and then one channel at a time onto the row of its note
    that fits best with the others sounding. Every comparison ranks complete mixes, each as the
    frame's hearing adds its rows up, by the spectral term. Two orders of pulses driven alike sound
    the same, so a combination reads once in either.

    The search also scores combinations for the judge: their spectral cost and their pulses' one order.
    """

    def __init__(
        self,
        fragment: Fragment,
        target: FitTarget,
        layout: StemLayout,
        catalogs: Mapping[GeneratorClassName, KindCatalog],
        matcher: FrameMatcher,
        hearing: FrameHearing,
    ) -> None:
        self.fragment = fragment
        self.target = target
        self.layout = layout
        self.catalogs = catalogs
        self.matcher = matcher
        self.hearing = hearing

    def fitted(self, proposals: Mapping[GeneratorClassName, Sequence[int]]) -> List[Rows]:
        """The distinct combinations fitting the frame best, each on the rows nearest its fitted levels.

        Every choice is fitted ``FIRST_UPDATES`` times and ranked, and its ``SURVIVORS`` cheapest
        ``FURTHER_UPDATES`` times more, so the longer fit goes to the choices that may win. The
        ``SCANNED_COMBINATIONS`` cheapest fits then move onto rows, cheapest first, until
        ``DISTINCT_COMBINATIONS`` distinct combinations stand: fits differing in levels alone may
        land on one combination. Equal costs keep the choices' order.

        Returns:
            Up to ``DISTINCT_COMBINATIONS`` combinations, by the cost of their fits, cheapest first.
        """
        choices = searched_choices(self.layout, proposals)
        channels = [
            ChannelUnits.of(choices, place, self.catalogs[slot.kind], self.hearing, self._bins)
            for place, slot in enumerate(self.layout.slots)
            if slot.plays_levels
        ]
        survivors = self._survivors(channels, *self._fixed_parts(choices))
        found: Dict[Rows, Rows] = {}
        for position in np.argsort(survivors.costs, kind="stable")[:SCANNED_COMBINATIONS]:
            levels = [level[position] for level in survivors.levels]
            rows = self._rows(choices[int(survivors.choices[position])], channels, levels)
            found.setdefault(self.canonical(rows), rows)
            if len(found) >= DISTINCT_COMBINATIONS:
                break

        return list(found.values())

    def refined(self, combinations: Sequence[Rows]) -> List[Combination]:
        """The combinations moved onto the rows of their notes that fit the frame best, one channel at a time.

        Over ``REFINEMENT_SWEEPS`` sweeps through the channels in layout order, each sounding channel
        of every combination in turn takes the row of its own note, or its silence, that gives the
        frame the lowest spectral cost with the other channels sounding. A sounding noise moves over
        every row it holds, since its shapes overlap too broadly for a fit to tell them apart. A
        silent channel stays silent, so a combination keeps within the stem's count of channels.

        Returns:
            The distinct combinations reached, the cheapest first, equal costs in the given order.
        """
        if not combinations:
            return []

        current = [list(rows) for rows in combinations]
        for _ in range(REFINEMENT_SWEEPS):
            for place in range(len(self.layout.slots)):
                self._move(current, place)

        reached = [tuple(rows) for rows in current]
        found: Dict[Rows, Combination] = {}
        for rows, cost in zip(reached, self.spectral_costs(reached)):
            found.setdefault(self.canonical(rows), Combination(rows=rows, cost=float(cost)))

        return sorted(found.values(), key=_cost_of)

    def spectral_costs(self, combinations: Sequence[Rows]) -> np.ndarray:
        """The spectral cost of the frame with each combination's rows sounding together."""
        powers = np.stack([self._power_of(rows) for rows in combinations])
        return self.matcher.spectral_costs(self.fragment, powers)

    def canonical(self, rows: Rows) -> Rows:
        """The rows with the pulses in one order wherever the two are driven alike, so one sound reads once."""
        pulses = self.layout.interchangeable_pulses
        if len(pulses) != 2:
            return rows

        ordered = list(rows)
        ordered[pulses[0]], ordered[pulses[1]] = sorted(rows[place] for place in pulses)
        return tuple(ordered)

    def _survivors(self, channels: Sequence[ChannelUnits], base: np.ndarray, base_powers: np.ndarray) -> Survivors:
        """The choices surviving the short fit, fitted further, every channel starting at its proposal's volume."""
        fits = ChoiceFits.of(channels, base, base_powers)
        levels = fits.fitted(self.target, [channel.starts[channel.entries] for channel in channels], FIRST_UPDATES)
        costs = self.matcher.spectral_costs(self.fragment, fits.powers(levels))
        cheapest = np.argsort(costs, kind="stable")[:SURVIVORS]
        kept = fits.kept(cheapest)
        levels = kept.fitted(self.target, [level[cheapest] for level in levels], FURTHER_UPDATES)
        return Survivors(
            choices=cheapest, levels=levels, costs=self.matcher.spectral_costs(self.fragment, kept.powers(levels))
        )

    @property
    def _bins(self) -> int:
        """How many bins the frame's feature holds."""
        return int(self.target.reference.shape[0])

    def _fixed_parts(self, choices: Sequence[Choice]) -> Tuple[np.ndarray, np.ndarray]:
        """Every choice's fixed part, in feature values and in power: the leak and its one-level channels' rows."""
        features = np.zeros((len(choices), self._bins)) + self.hearing.leak_features
        powers = np.zeros((len(choices), self._bins)) + self.hearing.leak
        for place, slot in enumerate(self.layout.slots):
            if slot.plays_levels:
                continue

            for position, choice in enumerate(choices):
                row = choice[place]
                if row is not None:
                    features[position] += self.hearing.features(place, [row])[0]
                    powers[position] += self.hearing.powers(place, [row])[0]

        return features, powers

    def _rows(self, choice: Choice, channels: Sequence[ChannelUnits], levels: Sequence[float]) -> Rows:
        """The rows ``choice`` plays at its fitted ``levels``: each fitted channel on the row of its unit's volume.

        A fitted channel plays the row of its unit's note and timbre nearest the volume its level
        sounds, which is silence under half a step. A one-level channel plays its proposal.
        """
        fitted = {channel.place: (channel, level) for channel, level in zip(channels, levels)}
        rows: List[int] = []
        for place, (slot, row) in enumerate(zip(self.layout.slots, choice)):
            catalog = self.catalogs[slot.kind]
            if row is None:
                rows.append(catalog.silence)
            elif place in fitted:
                channel, level = fitted[place]
                unit = channel.units[row]
                rows.append(catalog.nearest(unit.row, unit.volume_at(level)))
            else:
                rows.append(row)

        return tuple(rows)

    def _move(self, current: List[List[int]], place: int) -> None:
        """Moves the channel at ``place`` of every combination in ``current`` to its option sounding best with the rest.

        Every combination's options are scored in one batch. Of equally cheap options, the earlier
        stands.
        """
        movable = [
            (position, options)
            for position, rows in enumerate(current)
            if (options := self._options(place, rows)) is not None
        ]
        if not movable:
            return

        stacks = [
            self._without(place, current[position])[None, :] + self.hearing.powers(place, options)
            for position, options in movable
        ]
        costs = split_by_group(
            self.matcher.spectral_costs(self.fragment, np.concatenate(stacks)), [options for _, options in movable]
        )
        for (position, options), option_costs in zip(movable, costs):
            current[position][place] = cheapest_row(options, option_costs)

    def _options(self, place: int, rows: Sequence[int]) -> Optional[np.ndarray]:
        """The rows the channel at ``place`` may move to beside the rest of ``rows``; ``None`` where it is silent.

        A pulse or the triangle moves over the rows of its own note, in catalog order, and then its
        silence. The noise moves over every row it holds.
        """
        slot = self.layout.slots[place]
        catalog = self.catalogs[slot.kind]
        if not catalog.sounding(rows[place]):
            return None

        if slot.kind == GeneratorClassName.NOISE_GENERATOR:
            return np.arange(len(catalog.instructions))

        options: np.ndarray = np.append(catalog.rows_of(int(catalog.notes[rows[place]])), catalog.silence)
        return options

    def _without(self, place: int, rows: Sequence[int]) -> np.ndarray:
        """The power the frame holds with every channel of ``rows`` sounding but the one at ``place``."""
        return np.asarray(self._power_of(tuple(rows)) - self._row_power(place, rows[place]))

    def _power_of(self, rows: Rows) -> np.ndarray:
        """The power the frame holds with the rows sounding together, each as the hearing hears it on its channel."""
        total = self.hearing.leak
        for place, row in enumerate(rows):
            total = total + self._row_power(place, row)

        return total

    def _row_power(self, place: int, row: int) -> np.ndarray:
        """The power ``row`` adds to the frame on the channel at ``place``."""
        return np.asarray(self.hearing.powers(place, [row])[0])


def _cost_of(combination: Combination) -> float:
    return combination.cost
