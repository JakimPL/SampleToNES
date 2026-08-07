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

    def test_each_tag_finds_its_own_theme(self) -> None:
        default = _theme("global.theme.default")
        table = _theme("global.theme.table")
        ThemeRegistry.register(default)
        ThemeRegistry.register(table)

        assert (ThemeRegistry.get(default.tag), ThemeRegistry.get(table.tag)) == (default, table)

    def test_registering_a_tag_twice_keeps_the_later_theme(self) -> None:
        replacement = _theme("global.theme.default")
        ThemeRegistry.register(_theme("global.theme.default"))
        ThemeRegistry.register(replacement)

        assert ThemeRegistry.get("global.theme.default") is replacement

    def test_a_theme_given_by_hand_is_taken_over_the_default_tag(self) -> None:
        default = _theme("global.theme.default")
        given = _theme("global.theme.table")
        ThemeRegistry.register(default)

        assert ThemeRegistry.resolve(given, default.tag) is given

    def test_the_default_tag_answers_when_no_theme_is_given(self) -> None:
        default = _theme("global.theme.default")
        ThemeRegistry.register(default)

        assert ThemeRegistry.resolve(None, default.tag) is default
