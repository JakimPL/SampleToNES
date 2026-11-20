from typing import Final

import numpy as np
import pytest

from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.fit import (
    FitTarget,
    fitted_combinations,
    fitted_levels,
)

BINS: Final[int] = 6
FLOOR: Final[float] = 1e-9
ATOMS: Final[np.ndarray] = np.array(
    [
        [4.0, 0.0, 2.0, 0.0, 1.0, 0.0],
        [0.0, 3.0, 0.0, 1.5, 0.0, 0.5],
        [1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
    ]
)
LEVELS: Final[np.ndarray] = np.array([0.5, 0.2, 0.0])
UPDATES: Final[int] = 2000
LEVEL_TOLERANCE: Final[float] = 5e-3


def _target(reference: np.ndarray, beta: float) -> FitTarget:
    return FitTarget(reference=reference, weights=np.ones(BINS), floor=FLOOR, beta=beta)


class TestFittedLevels:
    @pytest.mark.parametrize("beta", [1.0, 2.0], ids=["kullback_leibler", "squared"])
    def test_every_atom_is_fitted_to_the_level_the_frame_holds_it_at(self, beta: float) -> None:
        target = _target(LEVELS @ ATOMS, beta)

        levels = fitted_levels(target, ATOMS, np.full(3, 10.0), start=0.05, updates=UPDATES)

        assert levels == pytest.approx(LEVELS, abs=LEVEL_TOLERANCE)

    def test_a_level_stays_under_the_most_its_channels_play(self) -> None:
        target = _target(LEVELS @ ATOMS, 1.0)

        levels = fitted_levels(target, ATOMS, np.array([0.3, 10.0, 10.0]), start=0.05, updates=UPDATES)

        assert levels[0] <= 0.3


class TestFittedCombinations:
    def test_each_combination_fits_its_channels_beside_its_fixed_part(self) -> None:
        target = _target(0.4 * ATOMS[0] + 0.7 * ATOMS[1] + ATOMS[2], 1.0)
        units = [np.stack([ATOMS[0], ATOMS[1]]), np.stack([ATOMS[1], ATOMS[0]])]
        base = np.stack([ATOMS[2], ATOMS[2]])
        starts = [np.full(2, 0.05), np.full(2, 0.05)]

        first, second = fitted_combinations(target, units, base, starts, [np.full(2, 10.0)] * 2, updates=UPDATES)

        assert (first[0], second[0]) == (pytest.approx(0.4, abs=1e-3), pytest.approx(0.7, abs=1e-3))
        assert (first[1], second[1]) == (pytest.approx(0.7, abs=1e-3), pytest.approx(0.4, abs=1e-3))

    def test_a_channel_s_level_stays_under_its_cap(self) -> None:
        target = _target(0.4 * ATOMS[0], 1.0)

        (levels,) = fitted_combinations(
            target, [ATOMS[0][None, :]], np.zeros((1, BINS)), [np.full(1, 0.05)], [np.full(1, 0.1)], updates=UPDATES
        )

        assert levels[0] == pytest.approx(0.1)
