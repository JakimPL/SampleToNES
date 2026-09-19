import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Final

import msgpack
import pytest

from sampletones_core.compatibility.kind import ObjectKind
from sampletones_core.configs import Config
from sampletones_core.constants.enums import SpectrumMethod
from sampletones_core.data import Metadata
from sampletones_core.library.data import InstructionLibraryData
from sampletones_core.library.state import (
    CONFIG_FIELD,
    METADATA_FIELD,
    VERSION_FIELD,
    LibraryHeader,
    LibraryState,
    library_state,
)
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.compatibility import LIBRARY_VERSION, archived

LIBRARY_NAME: Final[str] = "library.ins"
FOREIGN_APPLICATION: Final[str] = "Another application"
LATER_LIBRARY_VERSION: Final[str] = "99.0"
MALFORMED_VERSION: Final[str] = "not a version"
STORED_GAMMA: Final[int] = 50
STORED_SAMPLE_RATE: Final[int] = 22050


def _write_current(path: Path) -> None:
    InstructionLibraryData.create(Config(), {}).save(path)


def _write_stating(**metadata: str) -> Callable[[Path], None]:
    def write(path: Path) -> None:
        library = InstructionLibraryData.create(Config(), {})
        stated = library.metadata.model_copy(update=metadata)
        library.model_copy(update={"metadata": stated}).save(path)

    return write


def _write_stating_no_version(path: Path) -> None:
    payload = msgpack.unpackb(InstructionLibraryData.create(Config(), {}).serialize(), raw=False)
    del payload[METADATA_FIELD][VERSION_FIELD]
    path.write_bytes(msgpack.packb(payload, use_bin_type=True))


def _write_archived(path: Path) -> None:
    shutil.copyfile(archived(ObjectKind.LIBRARY, LIBRARY_VERSION), path)


def _write_bytes(content: bytes) -> Callable[[Path], None]:
    def write(path: Path) -> None:
        path.write_bytes(content)

    return write


class TestWhereALibraryFileStands(BaseTestSuite):
    """A library reads current exactly where this build loads it; any other file is out of date."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        write: Callable[[Path], None]
        expected: LibraryState

    test_cases = (
        TestCase(label="a library this build wrote", write=_write_current, expected=LibraryState.CURRENT),
        TestCase(label="the library the last release wrote", write=_write_archived, expected=LibraryState.OUTDATED),
        TestCase(
            label="a library a later build wrote",
            write=_write_stating(library_data_version=LATER_LIBRARY_VERSION),
            expected=LibraryState.OUTDATED,
        ),
        TestCase(
            label="a library stating a malformed version",
            write=_write_stating(library_data_version=MALFORMED_VERSION),
            expected=LibraryState.OUTDATED,
        ),
        TestCase(
            label="a library another application wrote",
            write=_write_stating(application_name=FOREIGN_APPLICATION),
            expected=LibraryState.OUTDATED,
        ),
        TestCase(label="a library stating no version", write=_write_stating_no_version, expected=LibraryState.OUTDATED),
        TestCase(label="an empty file", write=_write_bytes(b""), expected=LibraryState.OUTDATED),
        TestCase(label="bytes of no format", write=_write_bytes(b"\xc1" * 32), expected=LibraryState.OUTDATED),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_the_state_it_reads_as(self, test_case: TestCase, tmp_path: Path) -> None:
        path = tmp_path / LIBRARY_NAME
        test_case.write(path)

        assert library_state(path) is test_case.expected

    def test_a_path_holding_no_file_reads_as_missing(self, tmp_path: Path) -> None:
        assert library_state(tmp_path / LIBRARY_NAME) is LibraryState.MISSING


class TestTheSettingsALibraryStates:
    def test_they_read_as_the_library_was_built_for(self, tmp_path: Path) -> None:
        base = Config()
        library_config = base.library.model_copy(
            update={
                "spectrum_method": SpectrumMethod.FFT,
                "transformation_gamma": STORED_GAMMA,
                "sample_rate": STORED_SAMPLE_RATE,
            }
        )
        path = tmp_path / LIBRARY_NAME
        InstructionLibraryData.create(base.model_copy(update={"library": library_config}), {}).save(path)

        assert LibraryHeader.read(path).config == library_config

    def test_settings_stated_in_no_form_this_build_reads_read_as_none(self, tmp_path: Path) -> None:
        payload = msgpack.unpackb(InstructionLibraryData.create(Config(), {}).serialize(), raw=False)
        payload[CONFIG_FIELD] = "no settings"
        path = tmp_path / LIBRARY_NAME
        path.write_bytes(msgpack.packb(payload, use_bin_type=True))

        assert LibraryHeader.read(path).config is None

    def test_the_metadata_names_the_build_that_wrote_it(self, tmp_path: Path) -> None:
        path = tmp_path / LIBRARY_NAME
        _write_current(path)

        assert LibraryHeader.read(path).metadata == Metadata.default()


class TestWhatAHeaderReadRestsOn:
    def test_a_library_stores_its_header_ahead_of_its_entries(self) -> None:
        """The metadata and the settings lead the stored map, which keeps a header read to the
        first bytes of a library however many entries follow."""
        assert list(InstructionLibraryData.model_fields)[:2] == [METADATA_FIELD, CONFIG_FIELD]
