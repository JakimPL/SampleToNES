from pathlib import Path
from typing import Final, Tuple

import numpy as np

from sampletones_core.audio.io import UNIT_SCALE, load_audio, mix_scale, read_stems, scale_stems, write_wave
from sampletones_core.audio.processing import quantize
from sampletones_core.configs import Config

SAMPLE_RATE: Final[int] = Config().library.sample_rate
QUANTIZATION_LEVELS: Final[int] = Config().general.quantization_levels
SAMPLES: Final[int] = 64
LOUD_LEVEL: Final[float] = 0.6
QUIET_LEVEL: Final[float] = 0.2
HALF_SCALE: Final[float] = 0.5


def _write(path: Path, level: float, samples: int = SAMPLES) -> Path:
    write_wave(path, SAMPLE_RATE, np.full(samples, level, dtype=np.float32))
    return path


def _read(*paths: Path) -> Tuple[np.ndarray, ...]:
    return read_stems(paths, target_sample_rate=SAMPLE_RATE)


def _scaled(recordings: Tuple[np.ndarray, ...], scale: float, *, quantized: bool = False) -> Tuple[np.ndarray, ...]:
    return scale_stems(recordings, scale=scale, quantize=quantized, quantization_levels=QUANTIZATION_LEVELS)


class TestReadStems:
    """A set of recordings read onto one sample rate and one length, at the levels captured."""

    def test_the_recordings_keep_the_captured_levels(self, tmp_path: Path) -> None:
        louder, quieter = _read(_write(tmp_path / "loud.wav", LOUD_LEVEL), _write(tmp_path / "quiet.wav", QUIET_LEVEL))

        np.testing.assert_allclose(np.max(np.abs(louder)), LOUD_LEVEL, rtol=1e-6)
        np.testing.assert_allclose(np.max(np.abs(quieter)), QUIET_LEVEL, rtol=1e-6)

    def test_a_shorter_recording_runs_on_in_silence(self, tmp_path: Path) -> None:
        longer, shorter = _read(
            _write(tmp_path / "longer.wav", 0.5),
            _write(tmp_path / "shorter.wav", 0.5, samples=SAMPLES // 2),
        )

        assert len(shorter) == len(longer) == SAMPLES
        np.testing.assert_array_equal(shorter[SAMPLES // 2 :], np.zeros(SAMPLES // 2, dtype=np.float32))

    def test_no_paths_reach_no_recordings(self) -> None:
        assert _read() == ()


class TestMixScale:
    """The one factor a set is divided by, drawn from the peak of its mix."""

    def test_the_scale_is_the_peak_of_the_mix(self, tmp_path: Path) -> None:
        recordings = _read(_write(tmp_path / "loud.wav", LOUD_LEVEL), _write(tmp_path / "quiet.wav", QUIET_LEVEL))

        np.testing.assert_allclose(mix_scale(recordings, normalize=True), LOUD_LEVEL + QUIET_LEVEL, rtol=1e-6)

    def test_silence_takes_unit_scale(self, tmp_path: Path) -> None:
        """A set holding no sound has no peak to scale by, so it stays as it went in."""
        recordings = _read(_write(tmp_path / "silent.wav", 0.0))

        assert mix_scale(recordings, normalize=True) == UNIT_SCALE

    def test_a_set_left_unnormalized_takes_unit_scale(self, tmp_path: Path) -> None:
        recordings = _read(_write(tmp_path / "loud.wav", LOUD_LEVEL))

        assert mix_scale(recordings, normalize=False) == UNIT_SCALE

    def test_no_recordings_take_unit_scale(self) -> None:
        assert mix_scale((), normalize=True) == UNIT_SCALE


class TestScaleStems:
    """Every recording of a set divided by one factor, then quantized."""

    def test_one_recording_reaches_what_loading_it_alone_reaches(self, tmp_path: Path) -> None:
        """Scaling a lone recording by the peak of its own sum is normalizing it."""
        path = _write(tmp_path / "alone.wav", 0.4)
        recordings = _read(path)

        (loaded,) = _scaled(recordings, mix_scale(recordings, normalize=True))

        np.testing.assert_allclose(
            loaded,
            load_audio(path, target_sample_rate=SAMPLE_RATE, normalize=True, quantize=False),
        )

    def test_the_recordings_keep_their_balance(self, tmp_path: Path) -> None:
        louder, quieter = _scaled(
            _read(_write(tmp_path / "loud.wav", LOUD_LEVEL), _write(tmp_path / "quiet.wav", QUIET_LEVEL)),
            HALF_SCALE,
        )

        np.testing.assert_allclose(louder, (LOUD_LEVEL / QUIET_LEVEL) * quieter, rtol=1e-6)
        np.testing.assert_allclose(np.max(np.abs(louder)), LOUD_LEVEL / HALF_SCALE, rtol=1e-6)

    def test_the_set_scaled_by_its_own_mix_reaches_the_full_range(self, tmp_path: Path) -> None:
        recordings = _read(_write(tmp_path / "first.wav", LOUD_LEVEL), _write(tmp_path / "second.wav", QUIET_LEVEL))

        scaled = _scaled(recordings, mix_scale(recordings, normalize=True))

        np.testing.assert_allclose(np.max(np.abs(sum(scaled))), 1.0, rtol=1e-6)

    def test_quantization_follows_scaling(self, tmp_path: Path) -> None:
        recordings = _read(_write(tmp_path / "loud.wav", LOUD_LEVEL))

        (quantized,) = _scaled(recordings, HALF_SCALE, quantized=True)

        np.testing.assert_array_equal(
            quantized,
            quantize((recordings[0] / HALF_SCALE).astype(np.float32), levels=QUANTIZATION_LEVELS),
        )
