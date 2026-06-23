from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest

from sampletones_core.configs import Config, WeightsConfig
from sampletones_core.fft import Window
from sampletones_core.reconstructions.criterion import Criterion


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
