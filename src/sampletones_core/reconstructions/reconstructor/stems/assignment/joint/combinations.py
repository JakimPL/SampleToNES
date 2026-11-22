import itertools
from dataclasses import dataclass
from typing import Dict, Final, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from sampletones_core.constants.enums import GeneratorClassName
from sampletones_core.fft import Fragment
from sampletones_core.reconstructions.reconstructor.matching import FrameMatcher
from sampletones_shared.array import xp

from .catalog import FULL_VOLUME, KindCatalog
from .fit import FitTarget, fitted_combinations
from .hearing import FrameHearing
from .layout import Slot, StemLayout

FIRST_UPDATES: Final[int] = 5
FURTHER_UPDATES: Final[int] = 15
SURVIVORS: Final[int] = 160
DISTINCT_COMBINATIONS: Final[int] = 12
SCANNED_COMBINATIONS: Final[int] = 72
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


@dataclass(frozen=True)
class UnitTable:
    """What one fitted channel may play across a frame's combinations: one entry per proposal, silence first.

    A proposal's unit is the loudest row of its note and timbre at the channel's drive, so a fitted
    level of one sounds that row, and the level may rise as far as full volume.

    Attributes:
        positions: Each combination's entry.
        entries: Each proposal row's entry.
        features: Each entry's unit atom, in feature values.
        powers: Each entry's unit atom, in power.
        caps: Each entry's highest level.
        starts: Each entry's starting level, the proposal's own volume.
        loudest: Each entry's unit row.
        volumes: Each entry's unit row's volume.
    """

    positions: np.ndarray
    entries: Dict[int, int]
    features: np.ndarray
    powers: np.ndarray
    caps: np.ndarray
    starts: np.ndarray
    loudest: np.ndarray
    volumes: np.ndarray


class CombinationSearch:
    """Searches the combinations of a frame's proposed notes for the rows that fit the frame best together.

    Every combination of the proposals the stem's channels may sound together is fitted at once,
    each pulse and noise channel's level free and the triangle at its one level. The combinations
    fitting best are moved onto the library's rows, one channel at a time over every row of its note,
    and every comparison between them is made on complete mixes under the spectral term, each mix
    as the frame's hearing adds its rows up.
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

    def fitted(self, proposals: Mapping[GeneratorClassName, Sequence[int]]) -> List[Combination]:
        """The distinct combinations fitting the frame best, on the rows nearest their fitted levels.

        Returns:
            Up to ``DISTINCT_COMBINATIONS`` combinations, the cheapest first.
        """
        choices = self._choices(proposals)
        fitted_slots = [index for index, slot in enumerate(self.layout.slots) if _fitted_level(slot)]
        tables = [self._unit_table(choices, index) for index in fitted_slots]
        units = [table.features[table.positions] for table in tables]
        unit_powers = [table.powers[table.positions] for table in tables]
        caps = [table.caps[table.positions] for table in tables]
        base, base_powers = self._fixed(choices)

        levels = fitted_combinations(
            self.target,
            units,
            base,
            [table.starts[table.positions] for table in tables],
            caps,
            updates=FIRST_UPDATES,
        )
        costs = self._spectral_costs(_mixed(base_powers, unit_powers, levels))
        kept = np.argsort(costs, kind="stable")[:SURVIVORS]
        levels = fitted_combinations(
            self.target,
            [unit[kept] for unit in units],
            base[kept],
            [level[kept] for level in levels],
            [cap[kept] for cap in caps],
            updates=FURTHER_UPDATES,
        )
        costs = self._spectral_costs(_mixed(base_powers[kept], [power[kept] for power in unit_powers], levels))

        found: Dict[Rows, Combination] = {}
        for position in np.argsort(costs, kind="stable")[:SCANNED_COMBINATIONS]:
            combination = int(kept[position])
            volumes = {
                index: (table, float(table.volumes[table.positions[combination]] * np.sqrt(max(level[position], 0.0))))
                for index, table, level in zip(fitted_slots, tables, levels)
            }
            rows = self._rows(choices[combination], volumes)
            found.setdefault(self.canonical(rows), Combination(rows=rows, cost=float(costs[position])))
            if len(found) >= DISTINCT_COMBINATIONS:
                break

        return sorted(found.values(), key=lambda found_combination: found_combination.cost)

    def refined(self, combinations: Sequence[Combination]) -> List[Combination]:
        """The combinations moved onto the rows of their notes that fit the frame best, one channel at a time.

        Each sounding channel in turn takes the row of its own note, or its silence, that lowers the
        spectral cost of the frame most with the other channels sounding, over two sweeps. A sounding
        noise moves over every row it holds, since its shapes overlap too broadly for a fit to tell
        them apart.

        Returns:
            The distinct combinations reached, the cheapest first.
        """
        if not combinations:
            return []

        current = [list(combination.rows) for combination in combinations]
        for _ in range(REFINEMENT_SWEEPS):
            for index, slot in enumerate(self.layout.slots):
                self._moved(current, index, slot)

        costs = self._spectral_costs(np.stack([self.power_of(tuple(rows)) for rows in current]))
        found: Dict[Rows, Combination] = {}
        for rows, cost in zip(current, costs):
            found.setdefault(self.canonical(tuple(rows)), Combination(rows=tuple(rows), cost=float(cost)))

        return sorted(found.values(), key=lambda combination: combination.cost)

    def power_of(self, rows: Rows) -> np.ndarray:
        """The power the frame holds with the rows sounding together, each at the drive the stem gives its channel."""
        total = self.hearing.leak
        for index, row in enumerate(rows):
            total = total + self._row_power(index, row)

        return total

    def spectral_costs(self, combinations: Sequence[Rows]) -> np.ndarray:
        """The spectral cost of the frame with each combination's rows sounding together."""
        return self._spectral_costs(np.stack([self.power_of(rows) for rows in combinations]))

    def canonical(self, rows: Rows) -> Rows:
        """The rows with the pulses in one order wherever the two are driven alike, so one sound reads once."""
        pulses = self.layout.interchangeable_pulses
        if len(pulses) != 2:
            return rows

        ordered = list(rows)
        ordered[pulses[0]], ordered[pulses[1]] = sorted(rows[index] for index in pulses)
        return tuple(ordered)

    def _choices(self, proposals: Mapping[GeneratorClassName, Sequence[int]]) -> List[Choice]:
        """Every choice of proposal per channel the stem may sound together, within its count of channels."""
        kinds = sorted(self.layout.kinds)
        per_kind: List[List[Tuple[Optional[int], ...]]] = []
        for kind in kinds:
            count = len(self.layout.of_kind(kind))
            offered = [int(row) for row in proposals.get(kind, ())]
            options: List[Tuple[Optional[int], ...]] = [(None,) * count]
            for sounding in range(1, count + 1):
                for picked in itertools.combinations(offered, sounding):
                    options.append((*picked, *([None] * (count - sounding))))
            per_kind.append(options)

        choices: List[Choice] = []
        for picked_per_kind in itertools.product(*per_kind):
            by_kind = {kind: list(picked) for kind, picked in zip(kinds, picked_per_kind)}
            choice = tuple(by_kind[slot.kind].pop(0) for slot in self.layout.slots)
            if sum(row is not None for row in choice) <= self.layout.cap:
                choices.append(choice)

        return choices

    def _unit_table(self, choices: Sequence[Choice], index: int) -> UnitTable:
        """The unit atom, cap and starting level of every proposal one fitted channel may play."""
        slot = self.layout.slots[index]
        catalog = self.catalogs[slot.kind]
        offered = sorted({row for choice in choices if (row := choice[index]) is not None})
        entries = {row: position + 1 for position, row in enumerate(offered)}
        bins = self.target.reference.shape[0]
        loudest = [catalog.loudest(int(catalog.notes[row]), int(catalog.timbres[row])) for row in offered]
        volumes = [max(int(catalog.volumes[row]), 1) for row in loudest]
        return UnitTable(
            positions=np.array([SILENT_ENTRY if row is None else entries[row] for row in (c[index] for c in choices)]),
            entries=entries,
            features=np.concatenate([np.zeros((1, bins)), self.hearing.unit_features(index, loudest)]),
            powers=np.concatenate([np.zeros((1, bins)), self.hearing.unit_powers(index, loudest)]),
            caps=np.array([0.0, *((FULL_VOLUME / volume) ** 2 for volume in volumes)]),
            starts=np.array(
                [0.0, *((max(int(catalog.volumes[row]), 1) / volume) ** 2 for row, volume in zip(offered, volumes))]
            ),
            loudest=np.array([catalog.silence, *loudest]),
            volumes=np.array([0.0, *volumes], dtype=np.float64),
        )

    def _fixed(self, choices: Sequence[Choice]) -> Tuple[np.ndarray, np.ndarray]:
        """The part of every combination played at one level, what the frame holds before its rows included."""
        bins = self.target.reference.shape[0]
        features = np.zeros((len(choices), bins)) + self.hearing.leak_features
        powers = np.zeros((len(choices), bins)) + self.hearing.leak
        for index, slot in enumerate(self.layout.slots):
            if _fitted_level(slot):
                continue
            for position, choice in enumerate(choices):
                row = choice[index]
                if row is not None:
                    features[position] += self.hearing.features(index, [row])[0]
                    powers[position] += self.hearing.powers(index, [row])[0]

        return features, powers

    def _rows(self, choice: Choice, volumes: Mapping[int, Tuple[UnitTable, float]]) -> Rows:
        """The rows nearest a combination's fitted volumes, on each proposal's note and timbre."""
        rows: List[int] = []
        for index, (slot, row) in enumerate(zip(self.layout.slots, choice)):
            catalog = self.catalogs[slot.kind]
            if row is None:
                rows.append(catalog.silence)
            elif index in volumes:
                table, volume = volumes[index]
                unit = int(table.loudest[table.entries[row]])
                rows.append(catalog.nearest(unit, min(volume, float(FULL_VOLUME))))
            else:
                rows.append(row)

        return tuple(rows)

    def _row_power(self, index: int, row: int) -> np.ndarray:
        return np.asarray(self.hearing.powers(index, [row])[0])

    def _moved(self, current: List[List[int]], index: int, slot: Slot) -> None:
        """Every combination's channel moved to the row of its note, or its silence, that fits best with the rest."""
        stacks: List[np.ndarray] = []
        owners: List[Tuple[int, np.ndarray]] = []
        for position, rows in enumerate(current):
            options = self._options(slot, rows, index)
            if options is None:
                continue
            others = self.power_of(tuple(rows)) - self._row_power(index, rows[index])
            stacks.append(others[None, :] + self.hearing.powers(index, options))
            owners.append((position, options))

        if not stacks:
            return

        costs = self._spectral_costs(np.concatenate(stacks))
        start = 0
        for position, options in owners:
            current[position][index] = int(options[int(np.argmin(costs[start : start + len(options)]))])
            start += len(options)

    def _options(self, slot: Slot, rows: Sequence[int], index: int) -> Optional[np.ndarray]:
        """The rows a sounding channel may move to beside the rest of a combination; ``None`` for a silent one.

        A pulse or the triangle moves over the rows of its own note and its silence. The noise moves
        over every row it holds.
        """
        catalog = self.catalogs[slot.kind]
        if not catalog.sounding(rows[index]):
            return None

        if slot.kind == GeneratorClassName.NOISE_GENERATOR:
            return np.arange(len(catalog.instructions))

        options: np.ndarray = np.append(catalog.rows_of(int(catalog.notes[rows[index]])), catalog.silence)
        return options

    def _spectral_costs(self, powers: np.ndarray) -> np.ndarray:
        """The spectral cost of the frame with each row of ``powers`` sounding."""
        features = self.matcher.candidate_provider.features_of(xp.asarray(powers))
        return self.matcher.scorer.spectral_costs(self.fragment, features)


def _fitted_level(slot: Slot) -> bool:
    """Whether a channel's level is fitted; the triangle plays one level."""
    return slot.kind != GeneratorClassName.TRIANGLE_GENERATOR


def _mixed(base: np.ndarray, units: Sequence[np.ndarray], levels: Sequence[np.ndarray]) -> np.ndarray:
    """What every combination sounds: its fixed part and each fitted channel's unit at its level."""
    mixed = base.copy()
    for unit, level in zip(units, levels):
        mixed = mixed + level[:, None] * unit

    return mixed
