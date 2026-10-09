from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Final, List

import pytest

from sampletones_core.configs import Config
from sampletones_core.fft import Window
from sampletones_core.headless import library as headless_library
from sampletones_core.headless.library import ensure_library
from sampletones_core.library import InstructionLibrary, InstructionLibraryData
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

EARLIER_LIBRARY_VERSION: Final[str] = "2.0"


def _config_in(directory: Path) -> Config:
    config = Config()
    general = config.general.model_copy(update={"library_directory": str(directory)})
    return config.model_copy(update={"general": general})


def _library_path(config: Config) -> Path:
    library = InstructionLibrary.from_config(config)
    return library.get_path(library.create_key(config, Window.from_config(config)))


def _write_current(config: Config) -> None:
    InstructionLibraryData.create(config, {}).save(_library_path(config))


def _write_earlier(config: Config) -> None:
    library = InstructionLibraryData.create(config, {})
    stated = library.metadata.model_copy(update={"library_data_version": EARLIER_LIBRARY_VERSION})
    library.model_copy(update={"metadata": stated}).save(_library_path(config))


def _write_nothing(config: Config) -> None:
    del config


class TestTheLibraryAHeadlessConversionPrepares(BaseTestSuite):
    """A library this build reads is kept; any other is generated in its place."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        write: Callable[[Config], None]
        expected: bool

    test_cases = (
        TestCase(label="a library this build wrote", write=_write_current, expected=False),
        TestCase(label="a library another version built", write=_write_earlier, expected=True),
        TestCase(label="no library", write=_write_nothing, expected=True),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_whether_it_is_generated(
        self,
        test_case: TestCase,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        generated: List[Config] = []
        monkeypatch.setattr(headless_library, "generate_library", generated.append)
        config = _config_in(tmp_path)
        test_case.write(config)

        ensure_library(config)

        assert generated == ([config] if test_case.expected else [])
