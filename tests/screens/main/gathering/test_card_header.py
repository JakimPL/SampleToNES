from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
    SUF_COLLAPSE_STRIP,
    TAG_GLOBAL_THEME_COLLAPSE_HEADER,
    TAG_GLOBAL_THEME_COLLAPSE_HEADER_HOVERED,
)
from sampletones_application.tags.main import TAG_MAIN_CONVERTER_PANEL, TAG_MAIN_SOURCE_PANEL
from tests.suite.screens.screen import Screen


class TestACardHeaderUnderThePointer:
    """A card's header bar lights while the pointer rests on it and settles back once the pointer leaves.

    The pointer rests on the Converter's header bar, which lights. Then it moves to the Source settings
    header, and the first bar returns to its resting theme.
    """

    def test_the_bar_lights_and_settles(self, screen: Screen) -> None:
        strip = compose_tag(TAG_MAIN_CONVERTER_PANEL, SUF_COLLAPSE_STRIP)
        elsewhere = compose_tag(TAG_MAIN_SOURCE_PANEL, SUF_COLLAPSE_STRIP)

        def rest_on_the_bar(screen: Screen) -> None:
            screen.hand.hover(strip)

            screen.expect(
                lambda: screen.theme_of(strip), TAG_GLOBAL_THEME_COLLAPSE_HEADER_HOVERED.__eq__, description="lit"
            )

        def move_off(screen: Screen) -> None:
            screen.hand.scroll_into_view(elsewhere)
            screen.hand.hover(elsewhere)

            screen.expect(
                lambda: screen.theme_of(strip), TAG_GLOBAL_THEME_COLLAPSE_HEADER.__eq__, description="settled"
            )

        screen.scenario(rest_on_the_bar, move_off).run()
