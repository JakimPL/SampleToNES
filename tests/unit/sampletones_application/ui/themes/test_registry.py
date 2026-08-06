from typing import Iterator

import pytest

from sampletones_application.ui.themes.items import ThemeItems
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.ui.themes.theme import Theme


def _theme(tag: str) -> Theme:
    return Theme(tag=tag, items=ThemeItems())


@pytest.fixture(autouse=True)
def registry() -> Iterator[None]:
    ThemeRegistry.clear()
    yield
    ThemeRegistry.clear()


class TestRegisteredThemes:
    def test_a_registered_theme_is_found_by_its_tag(self) -> None:
        theme = _theme("global.theme.default")
        ThemeRegistry.register(theme)

        assert ThemeRegistry.get("global.theme.default") is theme

    def test_an_unregistered_tag_raises(self) -> None:
        with pytest.raises(KeyError):
            ThemeRegistry.get("global.theme.default")

    def test_the_whole_set_is_listed_for_an_operation_addressing_it_at_once(self) -> None:
        default = _theme("global.theme.default")
        table = _theme("global.theme.table")
        ThemeRegistry.register(default)
        ThemeRegistry.register(table)

        assert ThemeRegistry.themes() == (default, table)

    def test_registering_a_tag_twice_keeps_the_later_theme(self) -> None:
        replacement = _theme("global.theme.default")
        ThemeRegistry.register(_theme("global.theme.default"))
        ThemeRegistry.register(replacement)

        assert ThemeRegistry.themes() == (replacement,)
