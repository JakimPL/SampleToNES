import hashlib
from pathlib import Path
from typing import Final, List

import pytest

from sampletones_tools.calibration.config.samples import SampleReference, SamplesConfig
from sampletones_tools.calibration.samples import SampleChecksumError, fetch_samples, is_fetched

DATA: Final[bytes] = b"recording"
DOWNLOAD: Final[str] = "sampletones_tools.calibration.samples._download"
SLEEP: Final[str] = "sampletones_tools.calibration.samples.time.sleep"
PAUSE: Final[float] = 2.5


def _reference(name: str, sha256: str) -> SampleReference:
    return SampleReference(
        name=name,
        url=f"https://example.org/{name}.wav",
        file_name=f"{name}.wav",
        sha256=sha256,
        start_seconds=0.0,
        end_seconds=1.0,
        license="CC0 1.0",
        attribution="someone",
    )


def _config(sha256: str) -> SamplesConfig:
    return SamplesConfig(user_agent="test", pause_seconds=0.0, samples=[_reference("sample", sha256)])


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

    def test_downloads_pause_between_each_other_and_never_before_the_first(
        self, downloads: List[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        events: List[str] = []
        monkeypatch.setattr(SLEEP, lambda seconds: events.append(f"pause {seconds}"))
        checksum = hashlib.sha256(DATA).hexdigest()
        names = ("first", "kept", "second", "third")
        config = SamplesConfig(
            user_agent="test", pause_seconds=PAUSE, samples=[_reference(name, checksum) for name in names]
        )
        (tmp_path / "kept.wav").write_bytes(DATA)

        paths = fetch_samples(config, tmp_path)

        assert events == [f"pause {PAUSE}", f"pause {PAUSE}"]
        assert [Path(url).stem for url in downloads] == ["first", "second", "third"]
        assert paths == [tmp_path / f"{name}.wav" for name in names]

    def test_a_refused_download_leaves_no_partial_file(self, downloads: List[str], tmp_path: Path) -> None:
        with pytest.raises(SampleChecksumError):
            fetch_samples(_config("0" * 64), tmp_path)

        assert list(tmp_path.iterdir()) == []

    def test_a_recording_on_disk_of_another_checksum_is_fetched_again(
        self, downloads: List[str], tmp_path: Path
    ) -> None:
        config = _config(hashlib.sha256(DATA).hexdigest())
        (tmp_path / "sample.wav").write_bytes(b"altered")

        fetch_samples(config, tmp_path)

        assert len(downloads) == 1
        assert (tmp_path / "sample.wav").read_bytes() == DATA
