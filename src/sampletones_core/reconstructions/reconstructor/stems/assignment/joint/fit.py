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
STACKED_DOT: Final[str] = "...b,...b->..."


@dataclass(frozen=True)
class FitTarget:
    """A frame's feature as a fit of levels reads it: the bins, their weights and the floor both sides stand on.

    A fit explains the frame as ``floor + base + sum(level * atom)`` in feature values, every level
    nonnegative and under its cap, and measures it against ``reference + floor`` by the criterion's
    weighted beta-divergence. The spectral term is that divergence over a constant of the frame, so a
    level lowering the fit's divergence lowers the spectral term the search later ranks by. A squared
    distance is the beta-divergence of beta two up to its scale, and an absolute distance is fitted
    under the Kullback-Leibler divergence, of beta one.

    The fit updates every level multiplicatively, as a nonnegative factorization with its atoms held
    does. The divergence's slope along an atom is its rising part less its falling part, each summed
    over the atom's bins, and each update multiplies the level by the ratio of the falling part to the
    rising part. A positive level stays positive, and for a beta from one to two each update lowers
    the divergence, also where the level is then clipped at its cap.

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

    def slopes(self, mixed: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """The divergence's falling and rising parts in each bin of the model ``mixed``, or of each model in a stack.

        The divergence of a bin falls as the model rises toward the target and rises past it: its
        slope there is the rising part ``w * mixed^(beta - 1)`` less the falling part
        ``w * (reference + floor) * mixed^(beta - 2)``.
        """
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
    """How strongly each atom sounds when every atom is fitted to the frame at once, all in one model.

    The levels of all the atoms are fitted together, each clipped at its cap, over a fixed part the
    frame holds whatever the atoms play. A note the frame holds takes its level, and a note that
    would only cover other notes' partials is left with little, since the true notes explain the
    same bins with nothing over.

    Args:
        target: The frame.
        atoms: One atom per row, in feature values.
        caps: The highest level each atom may reach.
        base: The fixed part, in feature values.
        start: The level every atom starts from, above zero for it to move.
        updates: How many updates the fit runs.

    Returns:
        One level per atom.
    """
    levels = np.full(atoms.shape[0], start)
    for _ in range(updates):
        falling, rising = target.slopes(levels @ atoms + base + target.floor)
        levels = np.minimum(_shared_update(levels, atoms, falling, rising), caps)

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
    """The levels of every combination's channels, each combination its own model fitted on its own.

    A combination's model holds one unit per fitted channel, each scaled by the channel's level,
    over a fixed part holding the channels that play one level. All its channels' levels are
    updated together against the frame, each clipped at its cap. A unit holding no power, as a
    silent channel's does, holds its level at zero.

    Args:
        target: The frame.
        units: Each fitted channel's unit, one row per combination, in feature values.
        base: The fixed part of each combination, one row per combination.
        levels: Each fitted channel's starting level, one per combination.
        caps: Each fitted channel's highest level, one per combination.
        updates: How many updates the fit runs.

    Returns:
        Each fitted channel's levels, one per combination.
    """
    fitted = [np.asarray(level, dtype=np.float64) for level in levels]
    for _ in range(updates):
        falling, rising = target.slopes(_stacked_models(target, units, base, fitted))
        fitted = [
            np.minimum(_stacked_update(level, unit, falling, rising), cap)
            for level, unit, cap in zip(fitted, units, caps)
        ]

    return fitted


def _stacked_models(
    target: FitTarget, units: Sequence[np.ndarray], base: np.ndarray, levels: Sequence[np.ndarray]
) -> np.ndarray:
    """Every combination's model at ``levels``: the floor, its fixed part and each channel's unit at its level."""
    mixed = base + target.floor
    for level, unit in zip(levels, units):
        mixed = mixed + level[:, None] * unit

    return mixed


def _shared_update(levels: np.ndarray, atoms: np.ndarray, falling: np.ndarray, rising: np.ndarray) -> np.ndarray:
    """Every level of atoms sounding in one model, times the ratio of the model's falling to rising part along its atom.

    ``VANISHING`` keeps the ratio finite for an atom with no power in any bin the criterion weighs.
    """
    return np.asarray(levels * (atoms @ falling) / (atoms @ rising + VANISHING))


def _stacked_update(levels: np.ndarray, units: np.ndarray, falling: np.ndarray, rising: np.ndarray) -> np.ndarray:
    """Each combination's level of its unit, times the ratio of its own model's falling to rising part along it."""
    return np.asarray(
        levels * np.einsum(STACKED_DOT, units, falling) / (np.einsum(STACKED_DOT, units, rising) + VANISHING)
    )


def _fit_beta(criterion: Criterion) -> float:
    """The beta of the divergence a fit under ``criterion`` lowers.

    Raises:
        ValueError: If the criterion's spectral distance is unsupported.
    """
    match criterion.metric.distance:
        case SpectralDistance.BETA_DIVERGENCE:
            return criterion.metric.divergence_beta
        case SpectralDistance.SQUARED:
            return SQUARED_DISTANCE_BETA
        case SpectralDistance.ABSOLUTE:
            return ABSOLUTE_DISTANCE_BETA
        case _:
            raise ValueError(f"Unsupported spectral distance: {criterion.metric.distance}")
