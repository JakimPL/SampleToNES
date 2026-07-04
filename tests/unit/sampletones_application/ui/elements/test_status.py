from typing import Iterator
from unittest.mock import MagicMock

import pytest

from sampletones_application.constants.general import TAG_GLOBAL_THEME_STATUS
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.ui.themes.theme import Theme


@pytest.fixture
def status_theme() -> Iterator[Theme]:
    theme = Theme(tag=TAG_GLOBAL_THEME_STATUS, items=MagicMock())
    ThemeRegistry.register(theme)
    yield theme
    ThemeRegistry._registry.pop(TAG_GLOBAL_THEME_STATUS, None)


class TestStatusBarConstruction:
    """The status bar is an ordinary constructor-injected widget: each construction yields its
    own instance, and consumers reach the one built by the composition root only through their
    constructor argument."""

    def test_each_construction_yields_its_own_instance(self, status_theme: Theme) -> None:
        first = GUIStatusBar(display_time=1.0)
        second = GUIStatusBar(display_time=2.0)

        assert first is not second
        assert first.message is None
        assert second.message is None
