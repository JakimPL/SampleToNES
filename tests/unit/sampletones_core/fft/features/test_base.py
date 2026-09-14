from dataclasses import dataclass
from typing import Final

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, SpectrumMethod
from sampletones_core.fft import Fragment, Window
from sampletones_core.fft.features import FeatureExtractor, get_feature_extractor
from sampletones_core.generators import NoiseGenerator
from sampletones_core.instructions import NoiseInstruction
from sampletones_core.structures.histogram import Histogram
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseAutolabelTestCase

CONTRIBUTION: Final[NoiseInstruction] = NoiseInstruction(on=True, period=12, volume=6, short=False)
TONE_FREQUENCY: Final[float] = 330.0
TONE_AMPLITUDE: Final[float] = 0.3
TONE_FRAMES: Final[int] = 12
TARGET_FRAME: Final[int] = 6
MEAN_LEVEL: Final[float] = 0.02
POWER_GAIN: Final[float] = 0.5


def _extractor(method: SpectrumMethod, fast_difference: bool) -> FeatureExtractor:
    base = Config()
    config = base.model_copy(
        update={
            "library": base.library.model_copy(update={"spectrum_method": method}),
            "generation": base.generation.model_copy(
                update={
                    "calculation": base.generation.calculation.model_copy(update={"fast_difference": fast_difference})
                }
            ),
        }
    )
    return get_feature_extractor(config, Window.from_config(config))


def _target(extractor: FeatureExtractor) -> Fragment:
    sample_rate = extractor.config.library.sample_rate
    length = extractor.config.library.frame_length * TONE_FRAMES
    audio = TONE_AMPLITUDE * np.sin(2 * np.pi * TONE_FREQUENCY * np.arange(length) / sample_rate)
    return extractor.extract(audio.astype(np.float32))[TARGET_FRAME]


def _contribution_feature(extractor: FeatureExtractor) -> Histogram:
    generator = NoiseGenerator(extractor.config, ChannelName.NOISE)
    return extractor.reference_feature(generator.generate_sample(CONTRIBUTION))


class TestRemovingAnExpectation(BaseTestSuite):
    """
    An uncorrelated contribution takes its mean level out of the target's waveform and its power
    out of the target's spectrum, the same way whichever way a residual is otherwise measured.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        expected: None = None
        method: SpectrumMethod

        @property
        def label(self) -> str:
            return self.method.value

    test_cases = (
        TestCase(method=SpectrumMethod.FFT),
        TestCase(method=SpectrumMethod.LOG_SPACED_FFT),
        TestCase(method=SpectrumMethod.CQT),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_the_waveform_keeps_its_shape_beyond_the_mean(self, test_case: TestCase) -> None:
        extractor = _extractor(test_case.method, fast_difference=False)
        target = _target(extractor)

        residual = extractor.remove_expectation(target, MEAN_LEVEL, _contribution_feature(extractor), POWER_GAIN)

        np.testing.assert_allclose(residual.audio, target.audio - MEAN_LEVEL, rtol=1e-6)
        np.testing.assert_allclose(
            residual.windowed_audio,
            target.windowed_audio - MEAN_LEVEL * extractor.window.envelope,
            rtol=1e-6,
        )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_the_spectrum_keeps_the_power_beyond_the_contribution(self, test_case: TestCase) -> None:
        extractor = _extractor(test_case.method, fast_difference=False)
        target = _target(extractor)
        contribution = _contribution_feature(extractor)

        residual = extractor.remove_expectation(target, MEAN_LEVEL, contribution, POWER_GAIN)

        transformer = extractor.transformer
        left = np.maximum(
            transformer.backward(target.feature).values - POWER_GAIN * transformer.backward(contribution).values,
            0.0,
        )
        expected = transformer.forward(Histogram(edges=target.feature.edges, values=left.astype(np.float32)))
        np.testing.assert_allclose(residual.feature.values, expected.values, rtol=1e-4, atol=1e-7)

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_the_residual_stands_the_same_with_fast_difference_on(self, test_case: TestCase) -> None:
        measured = _extractor(test_case.method, fast_difference=False)
        fast = _extractor(test_case.method, fast_difference=True)

        slow_residual = measured.remove_expectation(
            _target(measured), MEAN_LEVEL, _contribution_feature(measured), POWER_GAIN
        )
        fast_residual = fast.remove_expectation(_target(fast), MEAN_LEVEL, _contribution_feature(fast), POWER_GAIN)

        np.testing.assert_array_equal(fast_residual.feature.values, slow_residual.feature.values)
        np.testing.assert_array_equal(fast_residual.audio, slow_residual.audio)
