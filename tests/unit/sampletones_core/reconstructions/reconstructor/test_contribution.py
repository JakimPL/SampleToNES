import numpy as np

from sampletones_core.fft import Fragment
from sampletones_core.reconstructions.reconstructor.contribution import Contribution


class TestTheSilenceOfAFrame:
    def test_a_channel_sounding_nothing_adds_no_power_over_the_frame_s_bins_and_no_waveform_over_its_samples(
        self, synthetic_fragment: Fragment
    ) -> None:
        bins, samples = len(synthetic_fragment.feature.values), synthetic_fragment.audio.shape[0]

        silence = Contribution.silence_of(synthetic_fragment)

        assert bins != samples
        assert silence.power.shape == (bins,)
        assert silence.expectation.shape == (samples,)
        assert not np.any(silence.power) and not np.any(silence.expectation)
        assert silence.variance == 0.0
        assert not silence.sounding
