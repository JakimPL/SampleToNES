from dataclasses import dataclass
from typing import Final, List

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, SpectralDistance
from sampletones_core.fft import Fragment, Window
from sampletones_core.fft.features import FeatureExtractor
from sampletones_core.instructions import PulseInstruction
from sampletones_core.reconstructions.criterion import Criterion
from sampletones_core.reconstructions.criterion.spectral import spectral_floor
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.fit import (
    ABSOLUTE_DISTANCE_BETA,
    SQUARED_DISTANCE_BETA,
    FitTarget,
    fitted_combinations,
    fitted_levels,
)
from sampletones_shared.array import to_numpy, xp
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

from ..conftest import JOINT_SIGNAL_LENGTH, rendered_fragment

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
BASE: Final[np.ndarray] = np.array([0.3, 0.0, 0.7, 0.0, 0.0, 1.2])
OPEN_CAPS: Final[np.ndarray] = np.full(3, 10.0)
TIGHT_CAP: Final[float] = 0.3
START: Final[float] = 0.05
UPDATES: Final[int] = 2000
TRACKED_UPDATES: Final[int] = 60
LEVEL_TOLERANCE: Final[float] = 5e-3
ROUNDING: Final[float] = 1e-12
BETAS: Final[List[float]] = [1.0, 2.0]
BETA_IDS: Final[List[str]] = ["kullback_leibler", "squared"]
PULSE: Final[PulseInstruction] = PulseInstruction(on=True, pitch=64, volume=12, duty_cycle=2)


@pytest.fixture(name="joint_criterion", scope="module")
def joint_criterion_fixture(config: Config, window: Window) -> Criterion:
    return Criterion(config, window, JOINT_SIGNAL_LENGTH)


@pytest.fixture(name="pulse_fragment", scope="module")
def pulse_fragment_fixture(config: Config, extractor: FeatureExtractor) -> Fragment:
    return rendered_fragment(config, extractor, {ChannelName.PULSE1: PULSE})


def _target(reference: np.ndarray, beta: float) -> FitTarget:
    return FitTarget(reference=reference, weights=np.ones(BINS), floor=FLOOR, beta=beta)


def _divergence(target: FitTarget, model: np.ndarray) -> float:
    """The weighted beta-divergence of ``model`` from the floored target, for beta one or two."""
    floored = target.reference + target.floor
    if target.beta == 1.0:
        terms = floored * np.log(floored / model) - floored + model
    else:
        terms = np.square(floored - model) / 2.0

    return float(np.sum(target.weights * terms))


class TestFittedLevels(BaseTestSuite):
    """Every atom fitted at once in one model, each level nonnegative and under its cap."""

    @pytest.mark.parametrize("beta", BETAS, ids=BETA_IDS)
    def test_every_atom_is_fitted_to_the_level_the_frame_holds_it_at(self, beta: float) -> None:
        target = _target(LEVELS @ ATOMS, beta)

        levels = fitted_levels(target, ATOMS, OPEN_CAPS, base=np.zeros(BINS), start=START, updates=UPDATES)

        assert levels == pytest.approx(LEVELS, abs=LEVEL_TOLERANCE)
        assert (levels >= 0.0).all()

    def test_the_atoms_are_fitted_over_the_fixed_part(self) -> None:
        target = _target(BASE + LEVELS @ ATOMS, 1.0)

        levels = fitted_levels(target, ATOMS, OPEN_CAPS, base=BASE, start=START, updates=UPDATES)

        assert levels == pytest.approx(LEVELS, abs=LEVEL_TOLERANCE)

    def test_a_level_the_frame_holds_beyond_its_cap_stops_at_the_cap(self) -> None:
        target = _target(LEVELS @ ATOMS, 1.0)
        caps = np.array([TIGHT_CAP, *OPEN_CAPS[1:]])

        levels = fitted_levels(target, ATOMS, caps, base=np.zeros(BINS), start=START, updates=UPDATES)

        assert levels[0] == TIGHT_CAP

    def test_a_level_starting_at_zero_stays_at_zero(self) -> None:
        target = _target(LEVELS @ ATOMS, 1.0)

        levels = fitted_levels(target, ATOMS, OPEN_CAPS, base=np.zeros(BINS), start=0.0, updates=UPDATES)

        assert not levels.any()

    @pytest.mark.parametrize("beta", BETAS, ids=BETA_IDS)
    @pytest.mark.parametrize("tight", [False, True], ids=["open", "at_a_cap"])
    def test_every_update_lowers_the_divergence(self, beta: float, tight: bool) -> None:
        """The multiplicative update lowers a beta-divergence of beta one to two, also with a level clipped at its cap."""
        target = _target(BASE + LEVELS @ ATOMS, beta)
        caps = np.array([TIGHT_CAP if tight else OPEN_CAPS[0], *OPEN_CAPS[1:]])

        divergences = [
            _divergence(
                target,
                fitted_levels(target, ATOMS, caps, base=BASE, start=START, updates=updates) @ ATOMS + BASE + FLOOR,
            )
            for updates in range(TRACKED_UPDATES)
        ]

        assert all(later <= earlier + ROUNDING for earlier, later in zip(divergences, divergences[1:]))
        assert divergences[-1] < divergences[0]


class TestFittedCombinations(BaseTestSuite):
    """Every combination its own model, its fitted channels' levels updated together against the frame."""

    def test_each_combination_fits_its_channels_beside_its_fixed_part(self) -> None:
        target = _target(0.4 * ATOMS[0] + 0.7 * ATOMS[1] + ATOMS[2], 1.0)
        units = [np.stack([ATOMS[0], ATOMS[1]]), np.stack([ATOMS[1], ATOMS[0]])]
        base = np.stack([ATOMS[2], ATOMS[2]])
        starts = [np.full(2, START), np.full(2, START)]

        first, second = fitted_combinations(target, units, base, starts, [np.full(2, 10.0)] * 2, updates=UPDATES)

        assert (first[0], second[0]) == (pytest.approx(0.4, abs=1e-3), pytest.approx(0.7, abs=1e-3))
        assert (first[1], second[1]) == (pytest.approx(0.7, abs=1e-3), pytest.approx(0.4, abs=1e-3))

    def test_a_channel_s_level_stays_under_its_cap(self) -> None:
        target = _target(0.4 * ATOMS[0], 1.0)

        (levels,) = fitted_combinations(
            target, [ATOMS[0][None, :]], np.zeros((1, BINS)), [np.full(1, START)], [np.full(1, 0.1)], updates=UPDATES
        )

        assert levels[0] == 0.1

    def test_a_silent_channel_stays_at_zero_beside_a_sounding_one(self) -> None:
        """A silent channel's unit holds no power, so it changes nothing of the other channels' fit."""
        target = _target(0.4 * ATOMS[0], 1.0)
        sounding = [ATOMS[0][None, :]]
        silent = [ATOMS[0][None, :], np.zeros((1, BINS))]
        caps = [np.full(1, 10.0), np.zeros(1)]

        (alone,) = fitted_combinations(
            target, sounding, np.zeros((1, BINS)), [np.full(1, START)], caps[:1], updates=UPDATES
        )
        beside, quiet = fitted_combinations(
            target, silent, np.zeros((1, BINS)), [np.full(1, START), np.zeros(1)], caps, updates=UPDATES
        )

        assert quiet[0] == 0.0
        assert beside[0] == alone[0]

    def test_a_combination_fits_its_units_as_one_model_holding_them_does(self) -> None:
        target = _target(BASE + LEVELS @ ATOMS, 1.0)

        stacked = fitted_combinations(
            target,
            [atom[None, :] for atom in ATOMS],
            BASE[None, :],
            [np.full(1, START) for _ in ATOMS],
            [np.full(1, cap) for cap in OPEN_CAPS],
            updates=TRACKED_UPDATES,
        )
        shared = fitted_levels(target, ATOMS, OPEN_CAPS, base=BASE, start=START, updates=TRACKED_UPDATES)

        assert np.concatenate(stacked) == pytest.approx(shared, rel=1e-7)


class TestTheFitTarget(BaseTestSuite):
    def test_the_slopes_balance_where_the_model_meets_the_target(self) -> None:
        target = _target(LEVELS @ ATOMS, 1.0)

        falling, rising = target.slopes(target.reference + target.floor)

        assert falling == pytest.approx(rising)

    def test_a_frame_s_target_reads_its_feature_the_criterion_s_weights_and_floor(
        self, joint_criterion: Criterion, pulse_fragment: Fragment
    ) -> None:
        target = FitTarget.of(pulse_fragment, joint_criterion)

        reference = np.asarray(to_numpy(pulse_fragment.feature.values), dtype=np.float64)
        floor = float(to_numpy(spectral_floor(xp.asarray(reference), metric=joint_criterion.metric)))
        assert np.array_equal(target.reference, reference)
        assert target.weights.shape == reference.shape
        assert target.floor == floor

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        distance: SpectralDistance
        beta: float
        expected: float

    test_cases = (
        TestCase(label="kullback_leibler", distance=SpectralDistance.BETA_DIVERGENCE, beta=1.0, expected=1.0),
        TestCase(label="beta_half", distance=SpectralDistance.BETA_DIVERGENCE, beta=0.5, expected=0.5),
        TestCase(label="squared", distance=SpectralDistance.SQUARED, beta=1.0, expected=SQUARED_DISTANCE_BETA),
        TestCase(label="absolute", distance=SpectralDistance.ABSOLUTE, beta=0.5, expected=ABSOLUTE_DISTANCE_BETA),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_criterion_s_distance_is_fitted_under_its_beta_divergence(
        self, test_case: TestCase, config: Config, window: Window, pulse_fragment: Fragment
    ) -> None:
        metric = config.generation.metric.model_copy(
            update={"spectral_distance": test_case.distance, "beta": test_case.beta}
        )
        measured = config.model_copy(update={"generation": config.generation.model_copy(update={"metric": metric})})

        target = FitTarget.of(pulse_fragment, Criterion(measured, window, JOINT_SIGNAL_LENGTH))

        assert target.beta == test_case.expected
