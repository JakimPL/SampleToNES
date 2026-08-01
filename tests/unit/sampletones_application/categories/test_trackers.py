from typing import Dict, FrozenSet, Set

import pytest

from sampletones_application.categories.trackers import (
    TRACKER_INSTRUMENT_FILTERS,
    TRACKER_INSTRUMENT_LABELS,
    TRACKER_PROJECT_ELEMENTS,
    TRACKER_PROJECT_MENU_LABELS,
    TRACKER_SAMPLE_MENU_LABELS,
)
from sampletones_application.utils.gui.shortcuts.ids import (
    PROJECT_EXPORT_SHORTCUT_IDS,
    SAMPLE_EXPORT_SHORTCUT_IDS,
)
from sampletones_core.trackers.backend import TrackerBackend
from sampletones_core.trackers.format import TrackerFormat
from sampletones_core.trackers.registry import build_tracker_backends
from sampletones_core.trackers.scope import ExportScope


@pytest.fixture(name="backends")
def backends_fixture() -> Dict[TrackerFormat, TrackerBackend]:
    return build_tracker_backends()


def formats_supporting(
    backends: Dict[TrackerFormat, TrackerBackend],
    scope: ExportScope,
) -> Set[TrackerFormat]:
    return {tracker_format for tracker_format, backend in backends.items() if scope in backend.supported_scopes}


class TestEveryOfferedFormatHasABackend:
    """A menu entry reaches a backend through the registry, so an entry the registry has no
    backend for would raise a ``KeyError`` the moment it is chosen."""

    @pytest.mark.parametrize(
        "offered",
        [
            frozenset(PROJECT_EXPORT_SHORTCUT_IDS),
            frozenset(SAMPLE_EXPORT_SHORTCUT_IDS),
            frozenset(TRACKER_PROJECT_MENU_LABELS),
            frozenset(TRACKER_SAMPLE_MENU_LABELS),
            frozenset(TRACKER_INSTRUMENT_LABELS),
            frozenset(TRACKER_INSTRUMENT_FILTERS),
            frozenset(TRACKER_PROJECT_ELEMENTS),
        ],
        ids=[
            "project_shortcuts",
            "sample_shortcuts",
            "project_menu",
            "sample_menu",
            "instrument_popup",
            "instrument_filters",
            "project_elements",
        ],
    )
    def test_the_registry_builds_every_offered_format(
        self,
        backends: Dict[TrackerFormat, TrackerBackend],
        offered: FrozenSet[TrackerFormat],
    ) -> None:
        assert offered <= frozenset(backends)


class TestTheMenusMatchTheSupportedScopes:
    """Each submenu lists exactly the formats whose backend writes that scope, so a format
    gains its entry by declaring the scope rather than by a second edit in the UI."""

    def test_the_project_export_menu_lists_the_formats_that_write_a_project(
        self,
        backends: Dict[TrackerFormat, TrackerBackend],
    ) -> None:
        assert set(TRACKER_PROJECT_MENU_LABELS) == formats_supporting(backends, ExportScope.PROJECT)

    def test_the_instruments_export_menu_lists_the_formats_that_write_a_sample(
        self,
        backends: Dict[TrackerFormat, TrackerBackend],
    ) -> None:
        assert set(TRACKER_SAMPLE_MENU_LABELS) == formats_supporting(backends, ExportScope.SAMPLE)

    def test_the_instrument_popup_lists_the_formats_that_write_one_slice(
        self,
        backends: Dict[TrackerFormat, TrackerBackend],
    ) -> None:
        assert set(TRACKER_INSTRUMENT_LABELS) == formats_supporting(backends, ExportScope.INSTRUMENT)


class TestEveryMenuEntryCarriesAnAction:
    """A submenu builds its entries by pairing a shortcut id with a label, so the two maps
    cover the same formats."""

    def test_the_project_menu_pairs_every_label_with_a_shortcut(self) -> None:
        assert set(TRACKER_PROJECT_MENU_LABELS) == set(PROJECT_EXPORT_SHORTCUT_IDS)

    def test_the_instruments_menu_pairs_every_label_with_a_shortcut(self) -> None:
        assert set(TRACKER_SAMPLE_MENU_LABELS) == set(SAMPLE_EXPORT_SHORTCUT_IDS)
