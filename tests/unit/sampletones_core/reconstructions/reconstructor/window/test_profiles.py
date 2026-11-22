from typing import Final

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.configs.library import InstructionsLibraryConfig
from sampletones_core.constants.enums import SpectrumMethod
from sampletones_core.fft import Window
from sampletones_core.fft.utils import calculate_n_bins
from sampletones_core.reconstructions.reconstructor.window.profiles import FrameProfiles, frame_profiles

WINDOWED_BINS: Final[int] = 16
LOWEST_BIN_OWN_SHARE: Final[float] = 0.1
SYMMETRY_TOLERANCE: Final[float] = 0.02


def _profiles(method: SpectrumMethod) -> FrameProfiles:
    config = Config(library=InstructionsLibraryConfig(spectrum_method=method))
    window = Window.from_config(config)
    bins = calculate_n_bins(config.library.sample_rate) if method == SpectrumMethod.CQT else WINDOWED_BINS
    return frame_profiles(config, window, bins)


@pytest.fixture(name="constant_q", scope="module")
def constant_q_fixture() -> FrameProfiles:
    return _profiles(SpectrumMethod.CQT)


class TestWhatEachBinReadsOfTheFrames:
    @pytest.mark.parametrize("method", list(SpectrumMethod), ids=[method.value for method in SpectrumMethod])
    def test_a_note_held_through_the_window_reaches_every_bin_whole(self, method: SpectrumMethod) -> None:
        profiles = _profiles(method)

        assert profiles.amplitude.sum(axis=0) == pytest.approx(1.0)
        assert profiles.energy.sum(axis=0) == pytest.approx(1.0)

    def test_a_low_bin_reads_mostly_the_frames_around_its_own(self, constant_q: FrameProfiles) -> None:
        assert constant_q.own_amplitude[0] < LOWEST_BIN_OWN_SHARE
        assert constant_q.reach > 1

    def test_a_high_bin_reads_its_own_frame_alone(self, constant_q: FrameProfiles) -> None:
        assert constant_q.own_amplitude[-1] == pytest.approx(1.0)
        assert constant_q.own_energy[-1] == pytest.approx(1.0)

    def test_a_wavelet_centered_on_the_frame_reads_both_sides_alike(self, constant_q: FrameProfiles) -> None:
        for offset in range(1, constant_q.reach + 1):
            assert constant_q.amplitude_at(offset) == pytest.approx(
                constant_q.amplitude_at(-offset), abs=SYMMETRY_TOLERANCE
            )

    @pytest.mark.parametrize("method", [SpectrumMethod.FFT, SpectrumMethod.LOG_SPACED_FFT], ids=["fft", "logfft"])
    def test_a_windowed_feature_reads_every_bin_through_one_window(self, method: SpectrumMethod) -> None:
        profiles = _profiles(method)

        assert np.allclose(profiles.amplitude, profiles.amplitude[:, :1])
        assert profiles.reach == 1
