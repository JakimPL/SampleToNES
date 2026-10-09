from dataclasses import dataclass

import pytest

from sampletones_core.constants.enums import SpectrumMethod
from sampletones_core.constants.spectrum import CQT_REFERENCE_CONTEXT_FACTOR
from sampletones_core.fft import Window
from sampletones_core.generators.implementation.noise import NoiseGenerator
from sampletones_core.instructions import NoiseInstruction
from tests.suite.analysis import analyzed_config
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase


class TestTheReferenceReadsASeamlessStretch(BaseTestSuite):
    """A constant-Q reference feature reads a stretch of its sample several windows long. The slowest
    long-mode noise outlasts every stored sample and loops with a seam, so the sample holds the whole
    stretch the reference reads, at every sample rate."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        sample_rate: int

    test_cases = (
        TestCase(label="22050 Hz", sample_rate=22050),
        TestCase(label="44100 Hz", sample_rate=44100),
        TestCase(label="96000 Hz", sample_rate=96000),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_slowest_noise_sample_holds_the_reference_context(self, test_case: TestCase) -> None:
        config = analyzed_config(SpectrumMethod.CQT, gamma=0)
        config = config.model_copy(
            update={"library": config.library.model_copy(update={"sample_rate": test_case.sample_rate})}
        )
        window = Window.from_config(config)

        sample = NoiseGenerator(config).generate_sample(NoiseInstruction(on=True, period=0, volume=15, short=False))

        assert len(sample.array) >= CQT_REFERENCE_CONTEXT_FACTOR * window.size
