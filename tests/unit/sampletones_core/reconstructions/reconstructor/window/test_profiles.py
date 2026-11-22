from dataclasses import dataclass
from typing import Final, List

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.configs.library import InstructionsLibraryConfig
from sampletones_core.constants.enums import SpectrumMethod
from sampletones_core.constants.spectrum import BINS_PER_OCTAVE, CQT_CUTOFF_FREQUENCY
from sampletones_core.fft import Window
from sampletones_core.fft.cqt.frequencies import calculate_cqt_frequencies
from sampletones_core.fft.features import FeatureExtractor, get_feature_extractor
from sampletones_core.fft.utils import calculate_n_bins
from sampletones_core.reconstructions.reconstructor.window.profiles import BinWindow, FrameProfiles, frame_profiles
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

FRAME_LENGTH: Final[int] = 4
WINDOWED_BINS: Final[int] = 16
LOWEST_BIN_OWN_SHARE: Final[float] = 0.1
ROUNDING: Final[float] = 1e-12
HELD_NOTE_TOLERANCE: Final[float] = 0.02
LINEAR_GAMMA: Final[int] = 0
BASS: Final[float] = 110.0
MIDDLE: Final[float] = 440.0
TREBLE: Final[float] = 1000.0
METHODS: Final[List[SpectrumMethod]] = list(SpectrumMethod)


def _config(method: SpectrumMethod) -> Config:
    return Config(library=InstructionsLibraryConfig(spectrum_method=method))


def _profiles(method: SpectrumMethod) -> FrameProfiles:
    config = _config(method)
    window = Window.from_config(config)
    bins = calculate_n_bins(config.library.sample_rate) if method == SpectrumMethod.CQT else WINDOWED_BINS
    return frame_profiles(config, window, bins)


def _window(positions: List[int], weights: List[float]) -> BinWindow:
    return BinWindow.placed(np.array(positions), np.array(weights, dtype=np.float64), FRAME_LENGTH)


@pytest.fixture(name="constant_q", scope="module")
def constant_q_fixture() -> FrameProfiles:
    return _profiles(SpectrumMethod.CQT)


@pytest.fixture(name="uneven")
def uneven_fixture() -> BinWindow:
    """A window weighing 1 on the frame before, 2 and 3 on the frame read and 4 on the frame after."""
    return _window([-1, 0, 3, 4], [1.0, 2.0, 3.0, 4.0])


@pytest.fixture(name="wide")
def wide_fixture() -> BinWindow:
    """A window weighing 1 on the frame before, 2 on the frame read and 3 and 4 on the two frames after."""
    return _window([-4, 0, 4, 8], [1.0, 2.0, 3.0, 4.0])


class TestABinWindow(BaseTestSuite):
    """A bin's window weighs samples, and each sample sounds what the frame it falls within plays."""

    def test_a_sample_falls_within_the_frame_its_position_lies_in(self) -> None:
        """The frame read holds the positions from zero to one short of the frame length."""
        positions = np.array([-FRAME_LENGTH - 1, -FRAME_LENGTH, -1, 0, FRAME_LENGTH - 1, FRAME_LENGTH])

        window = BinWindow.placed(positions, np.ones(positions.shape[0]), FRAME_LENGTH)

        assert window.offsets.tolist() == [-2, -1, -1, 0, 0, 1]

    def test_amplitude_shares_weigh_each_frame_s_weight_and_energy_shares_its_squared_weight(
        self, uneven: BinWindow
    ) -> None:
        assert uneven.amplitude_shares(1) == pytest.approx(np.array([1.0, 5.0, 4.0]) / 10.0)
        assert uneven.energy_shares(1) == pytest.approx(np.array([1.0, 13.0, 16.0]) / 30.0)

    def test_a_table_reaching_farther_than_the_window_holds_nothing_beyond_it(self, uneven: BinWindow) -> None:
        assert uneven.amplitude_shares(2) == pytest.approx(np.array([0.0, 1.0, 5.0, 4.0, 0.0]) / 10.0)
        assert uneven.energy_shares(2) == pytest.approx(np.array([0.0, 1.0, 13.0, 16.0, 0.0]) / 30.0)

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        positions: List[int]
        expected: int

    test_cases = (
        TestCase(label="after", positions=[0, 4, 8, 12], expected=3),
        TestCase(label="before", positions=[-12, -8, 0], expected=3),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_reach_is_the_farthest_frame_on_either_side(self, test_case: TestCase) -> None:
        window = _window(test_case.positions, [1.0] * len(test_case.positions))

        assert window.reach == test_case.expected


class TestATableOfBins(BaseTestSuite):
    """Bins whose windows reach differently share one table, read by the offset from the frame read."""

    def test_the_table_reaches_as_far_as_the_farthest_window(self, wide: BinWindow) -> None:
        narrow = _window([0, 1, 2, 3], [1.0, 1.0, 1.0, 1.0])

        profiles = FrameProfiles.of([narrow, wide])

        assert profiles.reach == wide.reach
        assert profiles.amplitude[:, 0] == pytest.approx(narrow.amplitude_shares(wide.reach))
        assert profiles.energy[:, 1] == pytest.approx(wide.energy_shares(wide.reach))

    def test_each_share_is_read_by_its_offset_from_the_frame_read(self, wide: BinWindow) -> None:
        profiles = FrameProfiles.of([wide])

        assert profiles.amplitude_at(-1)[0] == pytest.approx(0.1)
        assert profiles.own_amplitude[0] == pytest.approx(0.2)
        assert profiles.amplitude_at(2)[0] == pytest.approx(0.4)
        assert profiles.energy_at(-1)[0] == pytest.approx(1.0 / 30.0)
        assert profiles.own_energy[0] == pytest.approx(4.0 / 30.0)
        assert profiles.energy_at(2)[0] == pytest.approx(16.0 / 30.0)


class TestWhatEachBinReadsOfTheFrames(BaseTestSuite):
    """The profiles of the features the configuration analyzes with, under every spectrum method."""

    @pytest.mark.parametrize("method", METHODS, ids=[method.value for method in METHODS])
    def test_a_note_held_through_the_window_reaches_every_bin_whole(self, method: SpectrumMethod) -> None:
        profiles = _profiles(method)

        assert profiles.amplitude.sum(axis=0) == pytest.approx(1.0)
        assert profiles.energy.sum(axis=0) == pytest.approx(1.0)

    @pytest.mark.parametrize("method", METHODS, ids=[method.value for method in METHODS])
    def test_each_bin_weighs_the_frame_it_reads_above_any_other(self, method: SpectrumMethod) -> None:
        profiles = _profiles(method)

        assert (profiles.own_amplitude >= profiles.amplitude).all()
        assert (profiles.own_energy >= profiles.energy).all()

    @pytest.mark.parametrize("method", METHODS, ids=[method.value for method in METHODS])
    def test_a_window_centered_on_the_frame_reads_both_sides_alike(self, method: SpectrumMethod) -> None:
        """Alike within the share of one sample on a frame's boundary, a window's weight peaking at one.

        A window reaching past its frame is longer than the frame, and its weights sum to at least
        half its length, so one sample holds at most twice the frame length's reciprocal.
        """
        profiles = _profiles(method)
        sample_share = 2.0 / _config(method).library.frame_length

        for offset in range(1, profiles.reach + 1):
            assert profiles.amplitude_at(offset) == pytest.approx(profiles.amplitude_at(-offset), abs=sample_share)
            assert profiles.energy_at(offset) == pytest.approx(profiles.energy_at(-offset), abs=sample_share)

    def test_a_low_bin_reads_mostly_the_frames_around_its_own(self, constant_q: FrameProfiles) -> None:
        assert constant_q.own_amplitude[0] < LOWEST_BIN_OWN_SHARE
        assert constant_q.reach > 1

    def test_a_high_bin_reads_its_own_frame_alone(self, constant_q: FrameProfiles) -> None:
        assert constant_q.own_amplitude[-1] == pytest.approx(1.0)
        assert constant_q.own_energy[-1] == pytest.approx(1.0)

    def test_a_higher_bin_holds_at_least_as_much_of_its_weight_on_its_own_frame(
        self, constant_q: FrameProfiles
    ) -> None:
        """A higher bin reads a shorter wavelet, which spreads less of it over the frames around."""
        assert (np.diff(constant_q.own_amplitude) >= -ROUNDING).all()
        assert (np.diff(constant_q.own_energy) >= -ROUNDING).all()

    @pytest.mark.parametrize("method", [SpectrumMethod.FFT, SpectrumMethod.LOG_SPACED_FFT], ids=["fft", "logfft"])
    def test_a_windowed_feature_reads_every_bin_through_one_window_as_far_as_it_reaches(
        self, method: SpectrumMethod
    ) -> None:
        window = Window.from_config(_config(method))
        profiles = _profiles(method)
        before = -(window.left_offset // window.frame_length)
        after = (window.left_offset + window.size - 1) // window.frame_length

        assert np.allclose(profiles.amplitude, profiles.amplitude[:, :1])
        assert np.allclose(profiles.energy, profiles.energy[:, :1])
        assert profiles.reach == max(before, after)


class TestAHeldNoteAsTheFeatureReadsIt(BaseTestSuite):
    """A tone keeping its phase reaches a bin by the square of its frames' summed amplitude shares.

    The tone sounds a bin's center frequency at unit amplitude over a run of frames and is silent
    elsewhere. Each frame's reading of the bin is held against the model: the squared sum of the
    amplitude shares of the frames the tone sounds in, times what the bin reads of the tone held
    throughout. A cut tone also spreads a little of its negative frequency's power into the bin,
    which the model leaves out; that spread stays within ``HELD_NOTE_TOLERANCE`` of the steady
    reading. The run starts a whole reach into the audio, so every frame's window reads the audio's
    start as silence, as the model does.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        method: SpectrumMethod
        frequency: float
        one_frame: bool

    test_cases = (
        TestCase(label="cqt_bass_cut", method=SpectrumMethod.CQT, frequency=BASS, one_frame=False),
        TestCase(label="cqt_middle_cut", method=SpectrumMethod.CQT, frequency=MIDDLE, one_frame=False),
        TestCase(label="cqt_bass_one_frame", method=SpectrumMethod.CQT, frequency=BASS, one_frame=True),
        TestCase(label="fft_middle_cut", method=SpectrumMethod.FFT, frequency=MIDDLE, one_frame=False),
        TestCase(label="fft_treble_cut", method=SpectrumMethod.FFT, frequency=TREBLE, one_frame=False),
        TestCase(label="fft_middle_one_frame", method=SpectrumMethod.FFT, frequency=MIDDLE, one_frame=True),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_each_frame_reads_the_squared_shares_of_the_frames_the_tone_sounds_in(self, test_case: TestCase) -> None:
        reach = _profiles(test_case.method).reach
        held = 1 if test_case.one_frame else 2 * reach + 2

        self._assert_read_as_the_model_hears(test_case.method, test_case.frequency, range(reach, reach + held))

    @pytest.mark.xfail(
        strict=True,
        reason="The constant-Q extraction reads the audio's first half frame as silence, which the model hears sound.",
    )
    def test_a_tone_sounding_from_the_audio_s_start_reads_as_the_model_hears_it(self) -> None:
        reach = _profiles(SpectrumMethod.CQT).reach

        self._assert_read_as_the_model_hears(SpectrumMethod.CQT, MIDDLE, range(2 * reach + 2))

    def _assert_read_as_the_model_hears(self, method: SpectrumMethod, frequency: float, sounding: range) -> None:
        """Holds each frame's reading of a tone sounding through ``sounding`` against the model's."""
        config = Config(library=InstructionsLibraryConfig(spectrum_method=method, transformation_gamma=LINEAR_GAMMA))
        window = Window.from_config(config)
        extractor = get_feature_extractor(config, window)
        centered = self._bin_centered(method, frequency, window)
        reach = _profiles(method).reach
        through = 2 * reach + 1
        steady = self._readings(extractor, centered, range(through), through)[reach]
        bin_index = int(np.argmax(steady))
        frames = sounding.stop + through

        readings = self._readings(extractor, centered, sounding, frames)

        profiles = frame_profiles(config, window, steady.shape[0])
        for frame in range(frames):
            shares = self._held_shares(profiles, bin_index, sounding, frame)
            assert readings[frame, bin_index] == pytest.approx(
                shares**2 * steady[bin_index], abs=HELD_NOTE_TOLERANCE * steady[bin_index]
            )

    @staticmethod
    def _bin_centered(method: SpectrumMethod, frequency: float, window: Window) -> float:
        """The center frequency, nearest ``frequency``, of a bin the feature reads."""
        sample_rate = window.sample_rate
        if method == SpectrumMethod.CQT:
            centers = calculate_cqt_frequencies(calculate_n_bins(sample_rate), CQT_CUTOFF_FREQUENCY, BINS_PER_OCTAVE)
            return float(centers[int(np.argmin(np.abs(centers - frequency)))])

        resolution = sample_rate / window.size
        return float(round(frequency / resolution) * resolution)

    @staticmethod
    def _readings(extractor: FeatureExtractor, frequency: float, sounding: range, frames: int) -> np.ndarray:
        """Each frame's feature values of a tone at ``frequency`` sounding through ``sounding``, one row per frame."""
        frame_length = extractor.window.frame_length
        samples = np.arange(frames * frame_length)
        tone = np.cos(2.0 * np.pi * frequency * samples / extractor.sample_rate)
        heard = (samples >= sounding.start * frame_length) & (samples < sounding.stop * frame_length)
        fragments = extractor.extract(np.where(heard, tone, 0.0))
        return np.array([fragment.feature.values for fragment in fragments], dtype=np.float64)

    @staticmethod
    def _held_shares(profiles: FrameProfiles, bin_index: int, sounding: range, frame: int) -> float:
        """The bin's summed amplitude shares of the frames in ``sounding`` its window reads around ``frame``."""
        read = range(max(sounding.start, frame - profiles.reach), min(sounding.stop, frame + profiles.reach + 1))
        return float(sum(profiles.amplitude_at(other - frame)[bin_index] for other in read))
