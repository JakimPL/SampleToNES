from typing import Callable, Dict, Final

import pytest

from sampletones_application.paths import KEYBINDINGS_DIRECTORY
from sampletones_application.utils.gui.shortcuts.catalog import ShortcutCatalog
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.utils.gui.shortcuts.scheme import ShortcutScheme
from sampletones_application.utils.gui.shortcuts.source import ShortcutSource
from sampletones_application.utils.gui.shortcuts.written import WrittenShortcut

PROBE_SCHEME_NAME: Final[str] = "probe"

RebindScheme = Callable[[Dict[ShortcutId, WrittenShortcut]], ShortcutScheme]


@pytest.fixture(scope="session")
def shipped() -> ShortcutScheme:
    """The scheme the build ships, which a case starts from since a scheme answers every action."""
    return ShortcutCatalog.load(KEYBINDINGS_DIRECTORY).default


@pytest.fixture
def rebound(shipped: ShortcutScheme) -> RebindScheme:
    """Builds a scheme that differs from the shipped one in the actions a case names."""

    def build(overrides: Dict[ShortcutId, WrittenShortcut]) -> ShortcutScheme:
        return ShortcutScheme(
            name=PROBE_SCHEME_NAME,
            bindings={**shipped.bindings, **overrides},
        )

    return build


@pytest.fixture
def source(shipped: ShortcutScheme) -> ShortcutSource:
    return ShortcutSource(shipped)
