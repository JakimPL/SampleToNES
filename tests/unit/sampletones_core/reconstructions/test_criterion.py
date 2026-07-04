from __future__ import annotations

from typing import Final
from unittest.mock import MagicMock

import numpy as np
import pytest

from sampletones_core.configs import Config, MetricConfig, WeightsConfig
from sampletones_core.constants.enums import SpectralDistance, SpectrumMethod
from sampletones_core.fft import Window
from sampletones_core.reconstructions.criterion import Criterion
from sampletones_shared.array import to_numpy

LONG_SIGNAL_LENGTH: Final[int] = 1 << 20


def _criterion_with_distance(
    config: Config,
    window: Window,
    spectral_distance: SpectralDistance,
    beta: float = 1.0,
) -> Criterion:
    updated_config = config.model_copy(
        update={
            "generation": config.generation.model_copy(
                update={"metric": MetricConfig(spectral_distance=spectral_distance, beta=beta)}
            )
        }
    )
    return Criterion(updated_config, window, LONG_SIGNAL_LENGTH)


@pytest.fixture(scope="module")
def config() -> Config:
    return Config()


@pytest.fixture(scope="module")
def window(config: Config) -> Window:
    return Window.from_config(config)


@pytest.fixture(scope="module")
def criterion(config: Config, window: Window) -> Criterion:
    return Criterion(config, window, LONG_SIGNAL_LENGTH)


class TestCriterionRmse:
    def test_2d_reference_raises_value_error(
        self,
        criterion: Criterion,
        config: Config,
    ) -> None:
        reference = np.zeros((2, config.frame_length), dtype=np.float32)
        candidates = np.zeros((3, config.frame_length), dtype=np.float32)
        with pytest.raises(ValueError):
            criterion.rmse(reference, candidates)

    def test_1d_candidate_is_accepted(
        self,
        criterion: Criterion,
        config: Config,
    ) -> None:
        reference = np.zeros(config.frame_length, dtype=np.float32)
        candidate = np.zeros(config.frame_length, dtype=np.float32)
        result = criterion.rmse(reference, candidate, with_weights=False)
        assert result.shape == (1,)

    def test_candidates_width_mismatch_raises_value_error(
        self,
        criterion: Criterion,
        config: Config,
    ) -> None:
        reference = np.zeros(config.frame_length, dtype=np.float32)
        candidates = np.zeros((3, config.frame_length + 1), dtype=np.float32)
        with pytest.raises(ValueError):
            criterion.rmse(reference, candidates)


class TestCriterionTemporalLoss:
    def test_temporal_loss_is_invariant_under_common_scaling(
        self,
        criterion: Criterion,
        config: Config,
    ) -> None:
        """
        Normalizing by the target level makes the temporal term relative: scaling
        the target and the candidates together leaves the loss unchanged, so the
        spectral/temporal blend holds at every frame loudness.
        """
        generator = np.random.default_rng(0)
        audio = generator.standard_normal(config.frame_length).astype(np.float32)
        candidates = generator.standard_normal((2, config.frame_length)).astype(np.float32)

        base = to_numpy(criterion.temporal_loss(audio, candidates))
        scaled = to_numpy(criterion.temporal_loss(4.0 * audio, 4.0 * candidates))
        np.testing.assert_allclose(scaled, base, rtol=1e-5)

    def test_near_silent_target_normalizes_at_the_level_floor(
        self,
        criterion: Criterion,
        config: Config,
    ) -> None:
        """
        A silent target frame normalizes at the configured temporal level floor, so
        a candidate's cost equals its RMS divided by the floor and stays bounded.
        """
        audio = np.zeros(config.frame_length, dtype=np.float32)
        candidate = np.full((1, config.frame_length), 0.1, dtype=np.float32)
        loss = float(to_numpy(criterion.temporal_loss(audio, candidate))[0])
        assert loss == pytest.approx(0.1 / criterion.temporal_level_floor, rel=1e-5)


class TestCriterionGetLossWeights:
    def test_negative_weight_raises_value_error(self, window: Window) -> None:
        mock_config = MagicMock()
        mock_config.generation.weights.spectral_loss_weight = -1.0
        mock_config.generation.weights.temporal_loss_weight = 1.0
        with pytest.raises(ValueError):
            Criterion(mock_config, window, LONG_SIGNAL_LENGTH)

    def test_zero_total_weight_raises_value_error(
        self,
        config: Config,
        window: Window,
    ) -> None:
        zero_config = config.model_copy(
            update={
                "generation": config.generation.model_copy(
                    update={
                        "weights": WeightsConfig(
                            spectral_loss_weight=0.0,
                            temporal_loss_weight=0.0,
                        )
                    }
                )
            }
        )
        with pytest.raises(ValueError):
            Criterion(zero_config, window, LONG_SIGNAL_LENGTH)


class TestCriterionSpectralLoss:
    @pytest.fixture
    def bins(self, criterion: Criterion) -> int:
        return int(criterion.weights.shape[-1])

    def test_beta_divergence_is_zero_for_identical_spectrum(
        self,
        config: Config,
        window: Window,
        bins: int,
    ) -> None:
        criterion = _criterion_with_distance(config, window, SpectralDistance.BETA_DIVERGENCE, beta=1.0)
        reference = np.linspace(0.1, 1.0, bins, dtype=np.float32)
        loss = criterion.spectral_loss(reference, reference[None, :])
        assert float(loss[0]) == pytest.approx(0.0, abs=1e-6)

    def test_beta_divergence_is_non_negative_for_mismatched_spectrum(
        self,
        config: Config,
        window: Window,
        bins: int,
    ) -> None:
        criterion = _criterion_with_distance(config, window, SpectralDistance.BETA_DIVERGENCE, beta=1.0)
        reference = np.linspace(0.1, 1.0, bins, dtype=np.float32)
        candidates = np.stack([np.full(bins, 0.5, dtype=np.float32), np.zeros(bins, dtype=np.float32)])
        loss = criterion.spectral_loss(reference, candidates)
        assert bool(np.all(to_numpy(loss) >= 0.0))

    def test_spectral_loss_shape_matches_candidate_count(
        self,
        config: Config,
        window: Window,
        bins: int,
    ) -> None:
        for distance in SpectralDistance:
            criterion = _criterion_with_distance(config, window, distance)
            reference = np.linspace(0.1, 1.0, bins, dtype=np.float32)
            candidates = np.stack([reference, np.full(bins, 0.3, dtype=np.float32), np.zeros(bins, dtype=np.float32)])
            loss = criterion.spectral_loss(reference, candidates)
            assert to_numpy(loss).shape == (3,)

    def test_closer_spectrum_scores_lower_than_distant_one(
        self,
        config: Config,
        window: Window,
        bins: int,
    ) -> None:
        criterion = _criterion_with_distance(config, window, SpectralDistance.BETA_DIVERGENCE, beta=1.0)
        reference = np.linspace(0.1, 1.0, bins, dtype=np.float32)
        close = reference + np.float32(0.01)
        distant = reference + np.float32(0.5)
        loss = criterion.spectral_loss(reference, np.stack([close, distant]))
        assert float(loss[0]) < float(loss[1])


class TestCriterionCqtAxis:
    def test_spectral_loss_runs_on_cqt_bins(self, config: Config) -> None:
        cqt_config = config.model_copy(
            update={"library": config.library.model_copy(update={"spectrum_method": SpectrumMethod.CQT})}
        )
        cqt_window = Window.from_config(cqt_config)
        criterion = Criterion(cqt_config, cqt_window, LONG_SIGNAL_LENGTH)

        bins = int(criterion.weights.shape[-1])
        reference = np.linspace(0.1, 1.0, bins, dtype=np.float32)
        candidates = np.stack([reference, np.zeros(bins, dtype=np.float32)])

        loss = criterion.spectral_loss(reference, candidates)
        assert to_numpy(loss).shape == (2,)
        assert bool(np.all(to_numpy(loss) >= 0.0))


class TestCriterionReliabilityMask:
    SHORT_SIGNAL_LENGTH: Final[int] = 512

    @staticmethod
    def _cqt_criterion(config: Config, signal_length: int) -> Criterion:
        cqt_config = config.model_copy(
            update={"library": config.library.model_copy(update={"spectrum_method": SpectrumMethod.CQT})}
        )
        cqt_window = Window.from_config(cqt_config)
        return Criterion(cqt_config, cqt_window, signal_length)

    def test_short_signal_zeroes_low_bins_and_keeps_high_bins(self, config: Config) -> None:
        criterion = self._cqt_criterion(config, self.SHORT_SIGNAL_LENGTH)
        weights = to_numpy(criterion.weights)
        assert float(weights[0]) == 0.0
        assert float(weights[-1]) > 0.0
        assert int(np.count_nonzero(weights == 0.0)) > 0

    def test_long_signal_keeps_every_bin(self, config: Config) -> None:
        criterion = self._cqt_criterion(config, LONG_SIGNAL_LENGTH)
        weights = to_numpy(criterion.weights)
        assert bool(np.all(weights > 0.0))

    def test_masked_bins_do_not_affect_spectral_loss(self, config: Config) -> None:
        criterion = self._cqt_criterion(config, self.SHORT_SIGNAL_LENGTH)
        weights = to_numpy(criterion.weights)
        masked = weights == 0.0
        assert bool(masked.any())

        bins = int(weights.shape[-1])
        reference = np.linspace(0.1, 1.0, bins, dtype=np.float32)
        candidate = reference.copy()
        candidate[masked] = candidate[masked] + np.float32(0.5)

        loss = criterion.spectral_loss(reference, candidate[None, :])
        assert float(to_numpy(loss)[0]) == pytest.approx(0.0, abs=1e-6)

    def test_fft_method_keeps_every_bin_regardless_of_length(self, config: Config) -> None:
        fft_config = config.model_copy(
            update={"library": config.library.model_copy(update={"spectrum_method": SpectrumMethod.FFT})}
        )
        fft_window = Window.from_config(fft_config)
        criterion = Criterion(fft_config, fft_window, signal_length=1)
        weights = to_numpy(criterion.weights)
        assert bool(np.all(weights > 0.0))
