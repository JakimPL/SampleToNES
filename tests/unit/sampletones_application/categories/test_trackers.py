from typing import Dict, FrozenSet, Set

import pytest

from sampletones_application.categories.trackers import (
    TRACKER_PROJECT_ELEMENTS,
    TRACKER_PROJECT_MENU_LABELS,
)
from sampletones_application.utils.gui.shortcuts.ids import PROJECT_EXPORT_SHORTCUT_IDS
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
            frozenset(TRACKER_PROJECT_MENU_LABELS),
            frozenset(TRACKER_PROJECT_ELEMENTS),
        ],
        ids=[
            "project_shortcuts",
            "project_menu",
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
    """The project submenu lists exactly the formats whose backend writes a project, so a
    format gains its entry by declaring the scope rather than by a second edit in the UI.

    An instrument export names its format through the destination's extension, so the
    formats it reaches are covered where that resolution lives.
    """

    def test_the_project_export_menu_lists_the_formats_that_write_a_project(
        self,
        backends: Dict[TrackerFormat, TrackerBackend],
    ) -> None:
        assert set(TRACKER_PROJECT_MENU_LABELS) == formats_supporting(backends, ExportScope.PROJECT)


class TestEveryMenuEntryCarriesAnAction:
    """A submenu builds its entries by pairing a shortcut id with a label, so the two maps
    cover the same formats."""

    def test_the_project_menu_pairs_every_label_with_a_shortcut(self) -> None:
        assert set(TRACKER_PROJECT_MENU_LABELS) == set(PROJECT_EXPORT_SHORTCUT_IDS)
