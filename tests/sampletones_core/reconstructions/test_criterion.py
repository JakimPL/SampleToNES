from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest

from sampletones_core.configs import Config, MetricConfig, WeightsConfig
from sampletones_core.constants.enums import SpectralDistance, SpectrumMethod
from sampletones_core.fft import Window
from sampletones_core.reconstructions.criterion import Criterion


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
    return Criterion(updated_config, window)


@pytest.fixture(scope="module")
def config() -> Config:
    return Config()


@pytest.fixture(scope="module")
def window(config: Config) -> Window:
    return Window.from_config(config)


@pytest.fixture(scope="module")
def criterion(config: Config, window: Window) -> Criterion:
    return Criterion(config, window)


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


class TestCriterionGetLossWeights:
    def test_negative_weight_raises_value_error(self, window: Window) -> None:
        mock_config = MagicMock()
        mock_config.generation.weights.spectral_loss_weight = -1.0
        mock_config.generation.weights.temporal_loss_weight = 1.0
        with pytest.raises(ValueError):
            Criterion(mock_config, window)

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
            Criterion(zero_config, window)


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
        assert bool(np.all(np.asarray(loss) >= 0.0))

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
            assert np.asarray(loss).shape == (3,)

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
        criterion = Criterion(cqt_config, cqt_window)

        bins = int(criterion.weights.shape[-1])
        reference = np.linspace(0.1, 1.0, bins, dtype=np.float32)
        candidates = np.stack([reference, np.zeros(bins, dtype=np.float32)])

        loss = criterion.spectral_loss(reference, candidates)
        assert np.asarray(loss).shape == (2,)
        assert bool(np.all(np.asarray(loss) >= 0.0))
