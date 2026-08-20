from typing import Dict, FrozenSet, Set

import pytest

from sampletones_application.categories.exports import (
    EXPORT_INSTRUMENT_FILTERS,
    EXPORT_PROJECT_ELEMENTS,
    EXPORT_PROJECT_MENU_LABELS,
    EXPORT_SAMPLE_MENU_LABELS,
    INSTRUMENT_EXPORT_FORMATS,
)
from sampletones_application.utils.gui.shortcuts.ids import (
    PROJECT_EXPORT_SHORTCUT_IDS,
    SAMPLE_EXPORT_SHORTCUT_IDS,
)
from sampletones_core.exports.backend import ExportBackend
from sampletones_core.exports.format import ExportFormat
from sampletones_core.exports.registry import build_tracker_backends
from sampletones_core.exports.scope import ExportScope


@pytest.fixture(name="backends")
def backends_fixture() -> Dict[ExportFormat, ExportBackend]:
    return build_tracker_backends()


def formats_supporting(
    backends: Dict[ExportFormat, ExportBackend],
    scope: ExportScope,
) -> Set[ExportFormat]:
    return {export_format for export_format, backend in backends.items() if scope in backend.supported_scopes}


class TestEveryOfferedFormatHasABackend:
    """A menu entry reaches a backend through the registry, so an entry the registry has no
    backend for would raise a ``KeyError`` the moment it is chosen."""

    @pytest.mark.parametrize(
        "offered",
        [
            frozenset(PROJECT_EXPORT_SHORTCUT_IDS),
            frozenset(EXPORT_PROJECT_MENU_LABELS),
            frozenset(EXPORT_PROJECT_ELEMENTS),
            frozenset(SAMPLE_EXPORT_SHORTCUT_IDS),
            frozenset(EXPORT_SAMPLE_MENU_LABELS),
            frozenset(INSTRUMENT_EXPORT_FORMATS),
        ],
        ids=[
            "project_shortcuts",
            "project_menu",
            "project_elements",
            "sample_shortcuts",
            "sample_menu",
            "instrument_button",
        ],
    )
    def test_the_registry_builds_every_offered_format(
        self,
        backends: Dict[ExportFormat, ExportBackend],
        offered: FrozenSet[ExportFormat],
    ) -> None:
        assert offered <= frozenset(backends)


class TestTheMenusMatchTheSupportedScopes:
    """The project submenu lists exactly the formats whose backend writes a project, so a
    format gains its entry by declaring the scope rather than by a second edit in the UI.

    An instrument export offers a chosen few of the formats able to write its scope, so each
    offered format is required to write that scope while the reverse stays a curated choice.
    """

    def test_the_project_export_menu_lists_the_formats_that_write_a_project(
        self,
        backends: Dict[ExportFormat, ExportBackend],
    ) -> None:
        assert set(EXPORT_PROJECT_MENU_LABELS) == formats_supporting(backends, ExportScope.PROJECT)

    def test_the_instruments_menu_offers_formats_that_write_a_whole_sample(
        self,
        backends: Dict[ExportFormat, ExportBackend],
    ) -> None:
        assert set(EXPORT_SAMPLE_MENU_LABELS) <= formats_supporting(backends, ExportScope.SAMPLE)

    def test_the_instrument_button_offers_formats_that_write_one_slice(
        self,
        backends: Dict[ExportFormat, ExportBackend],
    ) -> None:
        assert set(INSTRUMENT_EXPORT_FORMATS) <= formats_supporting(backends, ExportScope.INSTRUMENT)


class TestEveryMenuEntryCarriesAnAction:
    """A submenu builds its entries by pairing a shortcut id with a label, so the two maps
    cover the same formats."""

    def test_the_project_menu_pairs_every_label_with_a_shortcut(self) -> None:
        assert set(EXPORT_PROJECT_MENU_LABELS) == set(PROJECT_EXPORT_SHORTCUT_IDS)

    def test_the_instruments_menu_pairs_every_label_with_a_shortcut(self) -> None:
        assert set(EXPORT_SAMPLE_MENU_LABELS) == set(SAMPLE_EXPORT_SHORTCUT_IDS)


class TestEveryOfferedFormatIsNamedInItsDialog:
    """A save dialog offers each format under its own file type, so a format an export offers
    without a type name would reach the dialog unnamed."""

    def test_every_instrument_export_format_carries_a_file_type(self) -> None:
        offered = set(INSTRUMENT_EXPORT_FORMATS) | set(EXPORT_SAMPLE_MENU_LABELS)
        assert offered <= set(EXPORT_INSTRUMENT_FILTERS)
