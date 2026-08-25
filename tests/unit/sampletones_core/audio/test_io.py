from pathlib import Path
from typing import Final

import numpy as np

from sampletones_core.audio.io import load_audio, load_stems, write_wave
from sampletones_core.configs import Config

SAMPLE_RATE: Final[int] = Config().library.sample_rate
QUANTIZATION_LEVELS: Final[int] = Config().general.quantization_levels
SAMPLES: Final[int] = 64


def _write(path: Path, level: float, samples: int = SAMPLES) -> Path:
    write_wave(path, SAMPLE_RATE, np.full(samples, level, dtype=np.float32))
    return path


def _load_stems(*paths: Path, normalize: bool = True, quantize: bool = False) -> tuple:
    return load_stems(
        paths,
        target_sample_rate=SAMPLE_RATE,
        normalize=normalize,
        quantize=quantize,
        quantization_levels=QUANTIZATION_LEVELS,
    )


class TestLoadStems:
    """A set of recordings loaded onto one scale and one length."""

    def test_one_recording_reaches_what_loading_it_alone_reaches(self, tmp_path: Path) -> None:
        """Scaling a lone recording by the peak of its own sum is normalizing it."""
        path = _write(tmp_path / "alone.wav", 0.4)

        (loaded,) = _load_stems(path)

        np.testing.assert_allclose(
            loaded,
            load_audio(path, target_sample_rate=SAMPLE_RATE, normalize=True, quantize=False),
        )

    def test_the_recordings_keep_the_balance_they_were_captured_in(self, tmp_path: Path) -> None:
        louder, quieter = _load_stems(
            _write(tmp_path / "loud.wav", 0.6),
            _write(tmp_path / "quiet.wav", 0.2),
        )

        np.testing.assert_allclose(louder, 3.0 * quieter, rtol=1e-6)

    def test_the_set_reaches_the_full_range(self, tmp_path: Path) -> None:
        recordings = _load_stems(
            _write(tmp_path / "first.wav", 0.6),
            _write(tmp_path / "second.wav", 0.2),
        )

        np.testing.assert_allclose(np.max(np.abs(sum(recordings))), 1.0, rtol=1e-6)

    def test_a_shorter_recording_runs_on_in_silence(self, tmp_path: Path) -> None:
        longer, shorter = _load_stems(
            _write(tmp_path / "longer.wav", 0.5),
            _write(tmp_path / "shorter.wav", 0.5, samples=SAMPLES // 2),
        )

        assert len(shorter) == len(longer) == SAMPLES
        np.testing.assert_array_equal(shorter[SAMPLES // 2 :], np.zeros(SAMPLES // 2, dtype=np.float32))

    def test_silence_stays_silent(self, tmp_path: Path) -> None:
        """A set holding no sound has no peak to scale by, so it comes back as it went in."""
        recordings = _load_stems(_write(tmp_path / "silent.wav", 0.0))

        np.testing.assert_array_equal(recordings[0], np.zeros(SAMPLES, dtype=np.float32))

    def test_unscaled_loading_keeps_the_captured_levels(self, tmp_path: Path) -> None:
        louder, quieter = _load_stems(
            _write(tmp_path / "loud.wav", 0.6),
            _write(tmp_path / "quiet.wav", 0.2),
            normalize=False,
        )

        np.testing.assert_allclose(np.max(np.abs(louder)), 0.6, rtol=1e-6)
        np.testing.assert_allclose(np.max(np.abs(quieter)), 0.2, rtol=1e-6)

    def test_no_paths_reach_no_recordings(self) -> None:
        assert _load_stems() == ()
