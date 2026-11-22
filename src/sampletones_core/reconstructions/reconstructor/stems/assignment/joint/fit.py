from dataclasses import dataclass
from typing import Final, List, Self, Sequence, Tuple

import numpy as np

from sampletones_core.constants.enums import SpectralDistance
from sampletones_core.fft import Fragment
from sampletones_core.reconstructions.criterion import Criterion
from sampletones_core.reconstructions.criterion.spectral import spectral_floor
from sampletones_shared.array import to_numpy, xp

SQUARED_DISTANCE_BETA: Final[float] = 2.0
ABSOLUTE_DISTANCE_BETA: Final[float] = 1.0
VANISHING: Final[float] = 1e-30


@dataclass(frozen=True)
class FitTarget:
    """A frame's feature as a fit of levels reads it: the bins, their weights and the floor both sides stand on.

    The fit measures with the criterion's own beta-divergence, so a level that lowers the fit's
    divergence lowers the spectral term the search later ranks by. A criterion measuring with
    another distance is fitted under the beta-divergence nearest it.

    Attributes:
        reference: The frame's feature values.
        weights: The criterion's weight of each bin.
        floor: The power every bin of both sides is measured above.
        beta: The beta of the divergence the levels are fitted under.
    """

    reference: np.ndarray
    weights: np.ndarray
    floor: float
    beta: float

    @classmethod
    def of(cls, fragment: Fragment, criterion: Criterion) -> Self:
        """The fit target of one frame under ``criterion``."""
        reference = np.asarray(to_numpy(fragment.feature.values), dtype=np.float64)
        floor = spectral_floor(xp.asarray(reference), metric=criterion.metric)
        return cls(
            reference=reference,
            weights=np.asarray(to_numpy(criterion.weights), dtype=np.float64).reshape(-1),
            floor=float(to_numpy(floor)),
            beta=_fit_beta(criterion),
        )

    def updated(self, levels: np.ndarray, atoms: np.ndarray, mixed: np.ndarray) -> np.ndarray:
        """One multiplicative update of every level, the mix they sound standing at ``mixed``.

        The update multiplies each level by the ratio of the divergence's falling and rising parts
        along its atom, which keeps a level positive and lowers the divergence.

        Args:
            levels: The levels, one per atom, or one per atom of each mix in a stack.
            atoms: The atoms the levels scale, one per row, or one per row of each mix.
            mixed: The mix the levels sound together with the floor, one per row of a stack.

        Returns:
            The updated levels.
        """
        return _stepped(levels, atoms, *self.slopes(mixed))

    def slopes(self, mixed: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """The divergence's falling and rising parts at ``mixed``, which every level sounding in it is updated by."""
        shrunk = mixed ** (self.beta - 2.0)
        return self.weights * (self.reference + self.floor) * shrunk, self.weights * shrunk * mixed


def fitted_levels(
    target: FitTarget,
    atoms: np.ndarray,
    caps: np.ndarray,
    *,
    base: np.ndarray,
    start: float,
    updates: int,
) -> np.ndarray:
    """How strongly each atom sounds when every atom is fitted to the frame at once.

    The levels of all the atoms are fitted together, each held under the most its channels can
    play, over a fixed part the frame holds whatever the atoms play. A note the frame holds takes
    its level, and a note that would only cover other notes' partials is left with little, since the
    true notes explain the same bins with nothing over.

    Args:
        target: The frame.
        atoms: One atom per row, in feature values.
        caps: The highest level each atom may reach.
        base: The fixed part, in feature values.
        start: The level every atom starts from.
        updates: How many updates the fit runs.

    Returns:
        One level per atom.
    """
    levels = np.full(atoms.shape[0], start)
    for _ in range(updates):
        mixed = levels @ atoms + base + target.floor
        levels = np.minimum(target.updated(levels, atoms, mixed), caps)

    return levels


def fitted_combinations(
    target: FitTarget,
    units: Sequence[np.ndarray],
    base: np.ndarray,
    levels: Sequence[np.ndarray],
    caps: Sequence[np.ndarray],
    *,
    updates: int,
) -> List[np.ndarray]:
    """The levels of every combination's channels, each combination fitted on its own.

    Every combination holds one unit atom per fitted channel and a fixed part, the channels that
    play one level only. Its channels' levels are updated together against the frame.

    Args:
        target: The frame.
        units: Each fitted channel's unit atom, one row per combination.
        base: The fixed part of each combination, one row per combination.
        levels: Each fitted channel's starting level, one per combination.
        caps: Each fitted channel's highest level, one per combination.
        updates: How many updates the fit runs.

    Returns:
        Each fitted channel's levels, one per combination.
    """
    fitted = [np.asarray(level, dtype=np.float64) for level in levels]
    for _ in range(updates):
        mixed = base + target.floor
        for level, unit in zip(fitted, units):
            mixed = mixed + level[:, None] * unit
        falling, rising = target.slopes(mixed)
        fitted = [
            np.minimum(_stepped(level, unit, falling, rising), cap) for level, unit, cap in zip(fitted, units, caps)
        ]

    return fitted


def _stepped(levels: np.ndarray, atoms: np.ndarray, falling: np.ndarray, rising: np.ndarray) -> np.ndarray:
    """Every level multiplied by the ratio of the divergence's falling and rising parts along its atom."""
    if atoms.ndim == 2 and falling.ndim == 1:
        stepped: np.ndarray = levels * (atoms @ falling) / (atoms @ rising + VANISHING)
    else:
        stepped = (
            levels
            * np.einsum("...b,...b->...", atoms, falling)
            / (np.einsum("...b,...b->...", atoms, rising) + VANISHING)
        )

    return stepped


def _fit_beta(criterion: Criterion) -> float:
    match criterion.metric.distance:
        case SpectralDistance.BETA_DIVERGENCE:
            return criterion.metric.divergence_beta
        case SpectralDistance.SQUARED:
            return SQUARED_DISTANCE_BETA
        case SpectralDistance.ABSOLUTE:
            return ABSOLUTE_DISTANCE_BETA
        case _:
            raise ValueError(f"Unsupported spectral distance: {criterion.metric.distance}")
