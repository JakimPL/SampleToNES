from typing import Final, Tuple

import pytest

from automation.screen import Screen
from automation.worlds.home import World, screen_filling_state
from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_application.config.profile import UserProfile
from sampletones_shared.distribution import SAMPLETONES_DOCUMENTATION_ADDRESS
from sampletones_shared.documentation.site import DocumentationSite
from tests.suite.screens.seeds.documentation import SHIPPED_INDEX, ShippedDocumentation, shipped_site

STILL_FRAMES: Final[int] = 20


def choose_documentation(screen: Screen) -> None:
    screen.menu.choose(MenuElements.GROUP_HELP, MenuElements.ITEM_HELP_DOCUMENTATION)


def one_page(opened: Tuple[object, ...]) -> bool:
    return len(opened) == 1


def expect_the_copied_index(screen: Screen) -> None:
    """The browser was handed the index of the copy in the reader's data folder, holding the shipped page."""
    [index] = screen.expect(screen.opened, one_page, description="the documentation handed to the browser")
    copy = DocumentationSite(UserProfile.user().documentation)
    assert index == copy.index
    assert index.read_text(encoding="utf-8") == SHIPPED_INDEX
    assert copy.read_stamp() == shipped_site().read_stamp()


class TestDocumentationOpens:
    """Help > Documentation copies the shipped pages into the reader's data folder and hands their index
    to the browser."""

    @pytest.fixture
    def world(self) -> World:
        return World(
            state=screen_filling_state(),
            application_config=None,
            config=None,
            files=(ShippedDocumentation(),),
        )

    def test_the_index_opens_from_the_reader_folder(self, screen: Screen) -> None:
        def choosing_hands_the_copy_to_the_browser(screen: Screen) -> None:
            choose_documentation(screen)

            expect_the_copied_index(screen)
            assert not screen.documentation_notice.is_shown()

        screen.scenario(choosing_hands_the_copy_to_the_browser).run()


class TestDocumentationMissing:
    """An installation without its pages says where the documentation lives online and opens nothing,
    and the same item opens the pages once they are there."""

    def test_the_notice_names_the_online_copy(self, screen: Screen) -> None:
        def a_notice_names_the_address(screen: Screen) -> None:
            choose_documentation(screen)

            screen.expect(screen.documentation_notice.is_shown, bool, description="the documentation notice")
            assert SAMPLETONES_DOCUMENTATION_ADDRESS in screen.documentation_notice.words()
            screen.frames(STILL_FRAMES)
            assert screen.opened() == ()

            screen.documentation_notice.dismiss()
            screen.expect(screen.documentation_notice.is_shown, lambda shown: not shown, description="the notice gone")

        def the_pages_open_once_they_are_there(screen: Screen) -> None:
            ShippedDocumentation().write()

            choose_documentation(screen)

            expect_the_copied_index(screen)
            assert not screen.documentation_notice.is_shown()

        screen.scenario(a_notice_names_the_address, the_pages_open_once_they_are_there).run()
