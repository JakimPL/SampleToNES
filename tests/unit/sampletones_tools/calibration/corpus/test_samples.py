import hashlib
from pathlib import Path
from typing import Final

import numpy as np

from sampletones_core.audio import write_wave
from sampletones_core.configs import Config
from sampletones_tools.calibration.config.samples import SampleReference, SamplesConfig
from sampletones_tools.calibration.corpus.families import Family
from sampletones_tools.calibration.corpus.samples import build_samples

RATE: Final[int] = Config().library.sample_rate


def _references(path: Path) -> SamplesConfig:
    reference = SampleReference(
        name="sample",
        url="https://example.org/sample.wav",
        file_name=path.name,
        sha256=hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else "0" * 64,
        start_seconds=0.5,
        end_seconds=1.0,
        license="CC0 1.0",
        attribution="someone",
    )
    return SamplesConfig(user_agent="test", pause_seconds=0.0, samples=[reference])


class TestBuildSamples:
    def test_a_fetched_recording_is_heard_through_its_window(self, tmp_path: Path) -> None:
        path = tmp_path / "sample.wav"
        write_wave(path, RATE, np.full(RATE, 0.25, dtype=np.float32))

        (sample,) = build_samples(Config(), references=_references(path), directory=tmp_path)

        assert sample.family is Family.SAMPLES and sample.listed
        assert sample.audio.shape == (RATE // 2,)

    def test_a_recording_not_fetched_yet_is_left_out(self, tmp_path: Path) -> None:
        assert build_samples(Config(), references=_references(tmp_path / "absent.wav"), directory=tmp_path) == []
