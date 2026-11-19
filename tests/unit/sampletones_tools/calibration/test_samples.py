import hashlib
from pathlib import Path
from typing import Final, List

import pytest

from sampletones_tools.calibration.config.samples import SampleReference, SamplesConfig
from sampletones_tools.calibration.samples import SampleChecksumError, fetch_samples, is_fetched

DATA: Final[bytes] = b"recording"
DOWNLOAD: Final[str] = "sampletones_tools.calibration.samples._download"


def _config(sha256: str) -> SamplesConfig:
    reference = SampleReference(
        name="sample",
        url="https://example.org/sample.wav",
        file_name="sample.wav",
        sha256=sha256,
        start_seconds=0.0,
        end_seconds=1.0,
        license="CC0 1.0",
        attribution="someone",
    )
    return SamplesConfig(user_agent="test", pause_seconds=0.0, samples=[reference])


@pytest.fixture(name="downloads")
def downloads_fixture(monkeypatch: pytest.MonkeyPatch) -> List[str]:
    fetched: List[str] = []

    def download(url: str, user_agent: str) -> bytes:
        fetched.append(url)
        return DATA

    monkeypatch.setattr(DOWNLOAD, download)
    return fetched


class TestFetchSamples:
    def test_a_download_matching_its_checksum_is_kept(self, downloads: List[str], tmp_path: Path) -> None:
        config = _config(hashlib.sha256(DATA).hexdigest())

        (path,) = fetch_samples(config, tmp_path)

        assert path.read_bytes() == DATA
        assert is_fetched(config.samples[0], tmp_path)

    def test_a_recording_already_fetched_is_downloaded_no_more(self, downloads: List[str], tmp_path: Path) -> None:
        config = _config(hashlib.sha256(DATA).hexdigest())
        fetch_samples(config, tmp_path)

        fetch_samples(config, tmp_path)

        assert len(downloads) == 1

    def test_a_download_of_another_checksum_is_refused_and_left_unwritten(
        self, downloads: List[str], tmp_path: Path
    ) -> None:
        with pytest.raises(SampleChecksumError, match="checksum differs"):
            fetch_samples(_config("0" * 64), tmp_path)

        assert not (tmp_path / "sample.wav").exists()
