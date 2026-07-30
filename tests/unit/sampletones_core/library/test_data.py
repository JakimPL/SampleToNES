from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional
from unittest.mock import patch

import pytest

from sampletones_core.configs import Config
from sampletones_core.data import Metadata
from sampletones_core.library.data import InstructionLibraryData
from sampletones_shared.application import SAMPLETONES_LIBRARY_DATA_VERSION
from sampletones_shared.exceptions import (
    DeserializationError,
    IncompatibleLibraryDataVersionError,
    InvalidLibraryDataValuesError,
    InvalidMetadataError,
    LoadLibraryError,
    UnhandledLibraryError,
)
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.errors import DIRECTORY_READ_ERRORS


def _library(metadata: Optional[Metadata] = None) -> InstructionLibraryData:
    library = InstructionLibraryData.create(Config(), {})
    if metadata is not None:
        library = library.model_copy(update={"metadata": metadata})

    return library


class TestRoundTrip:
    def test_save_load_round_trip(self, tmp_path: Path) -> None:
        library = _library()
        path = tmp_path / "demo.ins"

        library.save(path)
        loaded = InstructionLibraryData.load(path)

        assert list(loaded.items) == []
        assert loaded.config == library.config


class TestLoadRejectsForeignFiles:
    def test_garbage_file_raises_load_library_error(
        self,
        tmp_path: Path,
    ) -> None:
        foreign = tmp_path / "foreign.ins"
        foreign.write_bytes(b"garbage-not-a-flatbuffer")

        with pytest.raises(LoadLibraryError):
            InstructionLibraryData.load(foreign)


class TestLoadFileAccess(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        make_path: Callable[[Path], Path]

    test_cases = [
        TestCase(
            label="missing_file",
            make_path=lambda root: root / "fake.ins",
            expected=FileNotFoundError,
        ),
        TestCase(
            label="directory",
            make_path=lambda root: root,
            expected=DIRECTORY_READ_ERRORS,
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_inaccessible_path_raises(
        self,
        test_case: TestCase,
        tmp_path: Path,
    ) -> None:
        with pytest.raises(test_case.expected):
            InstructionLibraryData.load(test_case.make_path(tmp_path))


class TestMetadataValidation:
    def test_incompatible_version_propagates(self, tmp_path: Path) -> None:
        library = _library(Metadata(library_data_version="0.0"))
        path = tmp_path / "old.ins"
        library.save(path)

        with pytest.raises(IncompatibleLibraryDataVersionError) as exc_info:
            InstructionLibraryData.load(path)

        assert exc_info.value.actual_version == "0.0"
        assert exc_info.value.expected_version == SAMPLETONES_LIBRARY_DATA_VERSION

    def test_foreign_application_name_propagates(self, tmp_path: Path) -> None:
        library = _library(Metadata(application_name="Foreign"))
        path = tmp_path / "foreign.ins"
        library.save(path)

        with pytest.raises(InvalidMetadataError):
            InstructionLibraryData.load(path)


class TestLoadWrapping(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        side_effect: Exception

    test_cases = [
        TestCase(
            label="invalid_values_wrapped",
            side_effect=TypeError("bad field"),
            expected=InvalidLibraryDataValuesError,
        ),
        TestCase(
            label="unexpected_wrapped_as_unhandled",
            side_effect=RuntimeError("runtime_error"),
            expected=UnhandledLibraryError,
        ),
        TestCase(
            label="domain_error_propagates_unchanged",
            side_effect=DeserializationError("missing getter"),
            expected=DeserializationError,
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_load_maps_deserialize_error(
        self,
        test_case: TestCase,
        tmp_path: Path,
    ) -> None:
        path = tmp_path / "any.ins"
        path.write_bytes(b"x")
        with patch.object(
            InstructionLibraryData,
            "deserialize",
            side_effect=test_case.side_effect,
        ):
            with pytest.raises(test_case.expected):
                InstructionLibraryData.load(path)
