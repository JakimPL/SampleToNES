from pathlib import Path
from typing import Callable, Final, List, Tuple

import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import DEFAULT_CHANNELS
from sampletones_core.headless.conversion import runners
from sampletones_core.headless.conversion.request import ConversionRequest, classic_setup
from sampletones_core.headless.conversion.runners import reconstruct, reconstruct_directory, reconstruct_sources
from sampletones_core.reconstructions.converter import ConversionJob, DirectoryConversion
from sampletones_core.reconstructions.progress import ReconstructionReporter
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_shared.logger import LoggerProtocol
from tests.suite.files import empty_file

PREPARED: Final[str] = "library prepared"
CONVERTED: Final[str] = "converted"


class RecordedConversion:
    """A directory conversion that records its start in place of running."""

    def __init__(self, steps: List[str]) -> None:
        self.steps = steps

    def set_callbacks(self, **callbacks: Callable[..., None]) -> None:
        del callbacks

    def start(self) -> None:
        self.steps.append(CONVERTED)

    def wait(self) -> None:
        pass


class TestReconstruct:
    def test_recordings_are_mixed_into_one_file(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        calls: List[Tuple[Tuple[Path, ...], Path]] = []

        def reconstruct_sources(
            sources: Tuple[Path, ...], config: Config, stems: StemsConfig, output_path: Path
        ) -> None:
            del config, stems
            calls.append((sources, output_path))

        monkeypatch.setattr(runners, "reconstruct_sources", reconstruct_sources)
        source = empty_file(tmp_path, "song.wav")
        request = ConversionRequest(
            sources=(source,), stems=classic_setup(DEFAULT_CHANNELS), output_path=tmp_path / "x.stn"
        )

        reconstruct(request, Config())

        assert calls == [((source,), tmp_path / "x.stn")]

    def test_a_directory_is_walked(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        walked: List[Path] = []

        def reconstruct_directory(directory: Path, config: Config, stems: StemsConfig) -> None:
            del config, stems
            walked.append(directory)

        monkeypatch.setattr(runners, "reconstruct_directory", reconstruct_directory)
        request = ConversionRequest(sources=(tmp_path,), stems=classic_setup(DEFAULT_CHANNELS), output_path=None)

        reconstruct(request, Config())

        assert walked == [tmp_path]


class TestTheLibraryAConversionSearches:
    """A conversion prepares the library its configuration names before it reconstructs anything."""

    def test_recordings_are_reconstructed_once_it_is_prepared(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        steps: List[str] = []

        def ensure_library(config: Config) -> None:
            del config
            steps.append(PREPARED)

        def reconstruct_job(arguments: Tuple[None, ConversionJob, ReconstructionReporter]) -> None:
            del arguments
            steps.append(CONVERTED)

        monkeypatch.setattr(runners, "ensure_library", ensure_library)
        monkeypatch.setattr(runners, "Reconstructor", lambda config, channels: None)
        monkeypatch.setattr(runners, "reconstruct_job", reconstruct_job)
        source = empty_file(tmp_path, "song.wav")

        reconstruct_sources((source,), Config(), classic_setup(DEFAULT_CHANNELS), tmp_path / "x.stn")

        assert steps == [PREPARED, CONVERTED]

    def test_a_directory_is_walked_once_it_is_prepared(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        steps: List[str] = []

        def ensure_library(config: Config) -> None:
            del config
            steps.append(PREPARED)

        def converter(config: Config, conversion: DirectoryConversion, logger: LoggerProtocol) -> RecordedConversion:
            del config, conversion, logger
            return RecordedConversion(steps)

        monkeypatch.setattr(runners, "ensure_library", ensure_library)
        monkeypatch.setattr(runners, "ReconstructionConverter", converter)

        reconstruct_directory(tmp_path, Config(), classic_setup(DEFAULT_CHANNELS))

        assert steps == [PREPARED, CONVERTED]
