from typing import Final

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import SpectrumMethod
from sampletones_core.fft import Window
from sampletones_core.fft.layers import analysis_layers
from sampletones_core.reconstructions.criterion.weights import calculate_spectral_weights
from sampletones_shared.array import to_numpy
from tests.suite.base import BaseTestSuite

ADDED_WEIGHT: Final[float] = 0.5
SIGNAL_LENGTH: Final[int] = 735 * 120


def _weights(config: Config) -> np.ndarray:
    return np.asarray(to_numpy(calculate_spectral_weights(config, Window.from_config(config), SIGNAL_LENGTH)))


@pytest.fixture(name="layered", scope="module")
def layered_fixture() -> Config:
    return Config.model_validate(
        {"generation": {"layers": [{"method": SpectrumMethod.LOG_SPACED_FFT.value, "weight": ADDED_WEIGHT}]}}
    )


class TestTheWeightsOfStackedMethods(BaseTestSuite):
    """Each method's bins hold its layer's share of the weight, spread over them as the method weighs them alone."""

    def test_the_weights_average_one_over_every_bin(self, layered: Config) -> None:
        assert _weights(layered).mean() == pytest.approx(1.0)

    def test_each_method_holds_its_layer_s_share_of_the_weight(self, layered: Config) -> None:
        weights = _weights(layered)
        own = _weights(Config()).shape[0]

        assert weights[:own].sum() / weights.sum() == pytest.approx(1.0 / (1.0 + ADDED_WEIGHT))
        assert weights[own:].sum() / weights.sum() == pytest.approx(ADDED_WEIGHT / (1.0 + ADDED_WEIGHT))

    def test_each_method_weighs_its_bins_as_it_does_alone(self, layered: Config) -> None:
        weights = _weights(layered)
        alone = [_weights(layer.config) for layer in analysis_layers(layered)]
        own = alone[0].shape[0]

        for part, single in ((weights[:own], alone[0]), (weights[own:], alone[1])):
            assert part / part.sum() == pytest.approx(single / single.sum())
