from dataclasses import dataclass
from typing import Dict, Final, List, Optional

import pytest

from sampletones_core.paths import (
    EXT_FILE_BITPHASE,
    EXT_FILE_INSTRUMENT,
    EXT_FILE_JSON,
    EXT_FILE_MODULE,
)
from sampletones_core.trackers.backend import TrackerBackend
from sampletones_core.trackers.extensions import (
    default_scope_extension,
    format_for_extension,
    scope_extensions,
)
from sampletones_core.trackers.format import TrackerFormat
from sampletones_core.trackers.registry import build_tracker_backends
from sampletones_core.trackers.scope import ExportScope

UNKNOWN_EXTENSION: Final[str] = ".xm"
NO_EXTENSION: Final[str] = ""


@dataclass(frozen=True)
class ExtensionCase:
    scope: ExportScope
    extension: str
    expected: Optional[TrackerFormat]


EXTENSION_CASES: Final[List[ExtensionCase]] = [
    ExtensionCase(
        scope=ExportScope.INSTRUMENT,
        extension=EXT_FILE_INSTRUMENT,
        expected=TrackerFormat.FAMITRACKER,
    ),
    ExtensionCase(
        scope=ExportScope.INSTRUMENT,
        extension=EXT_FILE_BITPHASE,
        expected=TrackerFormat.BITPHASE,
    ),
    ExtensionCase(
        scope=ExportScope.INSTRUMENT,
        extension=EXT_FILE_JSON,
        expected=TrackerFormat.BITPHASE_PRESET,
    ),
    ExtensionCase(
        scope=ExportScope.SAMPLE,
        extension=EXT_FILE_JSON,
        expected=TrackerFormat.BITPHASE_PRESET,
    ),
    ExtensionCase(
        scope=ExportScope.PROJECT,
        extension=EXT_FILE_MODULE,
        expected=TrackerFormat.FAMITRACKER,
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
def backends_fixture() -> Dict[TrackerFormat, TrackerBackend]:
    return build_tracker_backends()


class TestScopeExtensions:
    def test_one_slice_may_be_saved_for_every_format(
        self,
        backends: Dict[TrackerFormat, TrackerBackend],
    ) -> None:
        assert set(scope_extensions(backends, ExportScope.INSTRUMENT)) == {
            EXT_FILE_INSTRUMENT,
            EXT_FILE_BITPHASE,
            EXT_FILE_JSON,
        }

    def test_a_project_reaches_only_the_formats_holding_a_whole_composition(
        self,
        backends: Dict[TrackerFormat, TrackerBackend],
    ) -> None:
        """A preset carries one instrument, so its extension stays off a project's list."""
        assert set(scope_extensions(backends, ExportScope.PROJECT)) == {
            EXT_FILE_MODULE,
            EXT_FILE_BITPHASE,
        }

    @pytest.mark.parametrize("scope", list(ExportScope), ids=lambda scope: str(scope))
    def test_each_extension_is_offered_once(
        self,
        backends: Dict[TrackerFormat, TrackerBackend],
        scope: ExportScope,
    ) -> None:
        extensions = scope_extensions(backends, scope)
        assert len(extensions) == len(set(extensions))

    def test_the_extensions_follow_the_order_the_backends_were_registered(
        self,
        backends: Dict[TrackerFormat, TrackerBackend],
    ) -> None:
        assert scope_extensions(backends, ExportScope.INSTRUMENT) == (
            EXT_FILE_INSTRUMENT,
            EXT_FILE_BITPHASE,
            EXT_FILE_JSON,
        )


class TestDefaultScopeExtension:
    @pytest.mark.parametrize("scope", list(ExportScope), ids=lambda scope: str(scope))
    def test_the_default_is_one_of_the_offered_extensions(
        self,
        backends: Dict[TrackerFormat, TrackerBackend],
        scope: ExportScope,
    ) -> None:
        assert default_scope_extension(backends, scope) in scope_extensions(backends, scope)

    @pytest.mark.parametrize("scope", list(ExportScope), ids=lambda scope: str(scope))
    def test_the_default_resolves_to_a_format(
        self,
        backends: Dict[TrackerFormat, TrackerBackend],
        scope: ExportScope,
    ) -> None:
        """A destination suggested under the default reaches a backend as it stands, so
        confirming the dialog untouched writes a file.
        """
        extension = default_scope_extension(backends, scope)
        assert format_for_extension(backends, scope, extension) is not None

    def test_a_scope_no_format_writes_is_refused(self) -> None:
        with pytest.raises(ValueError):
            default_scope_extension({}, ExportScope.INSTRUMENT)


class TestFormatForExtension:
    @pytest.mark.parametrize(
        "case",
        EXTENSION_CASES,
        ids=lambda case: f"{case.scope}{case.extension}",
    )
    def test_the_extension_names_the_format_that_writes_it(
        self,
        backends: Dict[TrackerFormat, TrackerBackend],
        case: ExtensionCase,
    ) -> None:
        assert format_for_extension(backends, case.scope, case.extension) == case.expected

    def test_an_extension_typed_in_capitals_reaches_the_same_format(
        self,
        backends: Dict[TrackerFormat, TrackerBackend],
    ) -> None:
        assert (
            format_for_extension(backends, ExportScope.INSTRUMENT, EXT_FILE_INSTRUMENT.upper())
            == TrackerFormat.FAMITRACKER
        )

    def test_a_format_that_cannot_express_the_scope_stays_unmatched(
        self,
        backends: Dict[TrackerFormat, TrackerBackend],
    ) -> None:
        """A preset holds one instrument, so a project named with its extension resolves
        to no format at all.
        """
        assert format_for_extension(backends, ExportScope.PROJECT, EXT_FILE_JSON) is None

    @pytest.mark.parametrize("scope", list(ExportScope), ids=lambda scope: str(scope))
    def test_every_offered_extension_resolves(
        self,
        backends: Dict[TrackerFormat, TrackerBackend],
        scope: ExportScope,
    ) -> None:
        """The dialog offers exactly what the resolution accepts, so a destination taking
        one of the offered extensions always names a backend.
        """
        for extension in scope_extensions(backends, scope):
            assert format_for_extension(backends, scope, extension) is not None
