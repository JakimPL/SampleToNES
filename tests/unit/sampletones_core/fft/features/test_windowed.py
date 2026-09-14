from dataclasses import dataclass
from typing import Final

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, SpectrumMethod
from sampletones_core.fft import Window
from sampletones_core.fft.features import get_feature_extractor
from sampletones_core.generators import PulseGenerator
from sampletones_core.instructions import PulseInstruction
from sampletones_core.reconstructions.criterion import Criterion
from sampletones_shared.array import to_numpy
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseAutolabelTestCase

TONE: Final[PulseInstruction] = PulseInstruction(on=True, pitch=57, volume=12, duty_cycle=2)
TILED_FRAMES: Final[int] = 12
EDGE_FRAMES: Final[int] = 1
SIGNAL_LENGTH: Final[int] = 1 << 20
OWN_ENTRY_COST: Final[float] = 1e-3


class TestAToneScoresItsOwnEntry(BaseTestSuite):
    """
    A pulse tone repeats one waveform, so every frame of it carries the spectrum its phases average
    to, and its library entry scores each frame as a match at every gamma. The frames at either end
    are read across the edge of the audio, so the interior is where the tone stands whole.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        expected: None = None
        method: SpectrumMethod
        gamma: int

        @property
        def label(self) -> str:
            return f"{self.method.value}_gamma_{self.gamma}"

    test_cases = (
        TestCase(method=SpectrumMethod.FFT, gamma=0),
        TestCase(method=SpectrumMethod.FFT, gamma=50),
        TestCase(method=SpectrumMethod.FFT, gamma=100),
        TestCase(method=SpectrumMethod.LOG_SPACED_FFT, gamma=0),
        TestCase(method=SpectrumMethod.LOG_SPACED_FFT, gamma=50),
        TestCase(method=SpectrumMethod.LOG_SPACED_FFT, gamma=100),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_every_frame_of_a_tone_matches_its_reference_feature(self, test_case: TestCase) -> None:
        base = Config()
        config = base.model_copy(
            update={
                "library": base.library.model_copy(
                    update={"spectrum_method": test_case.method, "transformation_gamma": test_case.gamma}
                )
            }
        )
        window = Window.from_config(config)
        extractor = get_feature_extractor(config, window)
        sample = PulseGenerator(config, ChannelName.PULSE1).generate_sample(TONE)

        reference = extractor.reference_feature(sample)
        frames = extractor.extract(np.asarray(sample.get_fragment(0, config.library.frame_length * TILED_FRAMES)))
        criterion = Criterion(config, window, SIGNAL_LENGTH)
        costs = [
            float(to_numpy(criterion.spectral_loss(frame.feature, reference))[0])
            for frame in frames[EDGE_FRAMES:-EDGE_FRAMES]
        ]

        assert max(costs) < OWN_ENTRY_COST
