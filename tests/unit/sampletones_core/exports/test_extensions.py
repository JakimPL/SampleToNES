from dataclasses import dataclass
from typing import Dict, Final, List, Optional

import pytest

from sampletones_core.exports.backend import ExportBackend
from sampletones_core.exports.extensions import format_for_extension
from sampletones_core.exports.format import ExportFormat
from sampletones_core.exports.registry import build_tracker_backends
from sampletones_core.exports.scope import ExportScope
from sampletones_shared.paths.extensions import (
    EXT_FILE_BITPHASE,
    EXT_FILE_INSTRUMENT,
    EXT_FILE_JSON,
    EXT_FILE_MODULE,
)

UNKNOWN_EXTENSION: Final[str] = ".xm"
NO_EXTENSION: Final[str] = ""


@dataclass(frozen=True)
class ExtensionCase:
    scope: ExportScope
    extension: str
    expected: Optional[ExportFormat]


EXTENSION_CASES: Final[List[ExtensionCase]] = [
    ExtensionCase(
        scope=ExportScope.INSTRUMENT,
        extension=EXT_FILE_INSTRUMENT,
        expected=ExportFormat.FAMITRACKER,
    ),
    ExtensionCase(
        scope=ExportScope.INSTRUMENT,
        extension=EXT_FILE_BITPHASE,
        expected=ExportFormat.BITPHASE,
    ),
    ExtensionCase(
        scope=ExportScope.INSTRUMENT,
        extension=EXT_FILE_JSON,
        expected=ExportFormat.BITPHASE_PRESET,
    ),
    ExtensionCase(
        scope=ExportScope.SAMPLE,
        extension=EXT_FILE_JSON,
        expected=ExportFormat.BITPHASE_PRESET,
    ),
    ExtensionCase(
        scope=ExportScope.PROJECT,
        extension=EXT_FILE_MODULE,
        expected=ExportFormat.FAMITRACKER,
    ),
    ExtensionCase(
        scope=ExportScope.INSTRUMENT,
        extension=UNKNOWN_EXTENSION,
        expected=None,
    ),
    ExtensionCase(
        scope=ExportScope.INSTRUMENT,
        extension=NO_EXTENSION,
        expected=None,
    ),
]


@pytest.fixture(name="backends")
def backends_fixture() -> Dict[ExportFormat, ExportBackend]:
    return build_tracker_backends()


class TestFormatForExtension:
    @pytest.mark.parametrize(
        "case",
        EXTENSION_CASES,
        ids=lambda case: f"{case.scope}{case.extension}",
    )
    def test_the_extension_names_the_format_that_writes_it(
        self,
        backends: Dict[ExportFormat, ExportBackend],
        case: ExtensionCase,
    ) -> None:
        assert format_for_extension(backends, case.scope, case.extension) == case.expected

    def test_an_extension_typed_in_capitals_reaches_the_same_format(
        self,
        backends: Dict[ExportFormat, ExportBackend],
    ) -> None:
        assert (
            format_for_extension(backends, ExportScope.INSTRUMENT, EXT_FILE_INSTRUMENT.upper())
            == ExportFormat.FAMITRACKER
        )

    def test_a_format_that_cannot_express_the_scope_stays_unmatched(
        self,
        backends: Dict[ExportFormat, ExportBackend],
    ) -> None:
        """A preset holds one instrument, so a project named with its extension resolves
        to no format at all.
        """
        assert format_for_extension(backends, ExportScope.PROJECT, EXT_FILE_JSON) is None

    @pytest.mark.parametrize("scope", list(ExportScope), ids=lambda scope: str(scope))
    def test_every_extension_a_backend_writes_resolves_back_to_it(
        self,
        backends: Dict[ExportFormat, ExportBackend],
        scope: ExportScope,
    ) -> None:
        """A dialog offers the extension of each format it can reach, so a destination taking
        one of them names the backend that put it in the selector. Each scope's extensions are
        therefore distinct across formats, which is what the resolution reads them as.
        """
        for export_format, backend in backends.items():
            if scope in backend.supported_scopes:
                assert format_for_extension(backends, scope, backend.extension(scope)) == export_format
