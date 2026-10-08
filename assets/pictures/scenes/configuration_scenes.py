from typing import Final

from assets.pictures.paths import guide_picture
from assets.pictures.writer import Pictures
from automation.screen import Screen
from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_application.tags.main import (
    TAG_MAIN_ADVANCED_PANEL,
    TAG_MAIN_CONFIG_PANEL,
)

PAGE: Final[str] = "configuration"


class ConfigurationScenes:
    """The settings cards of the Main tab: General settings as the tab opens, and Advanced settings once shown."""

    def picture_general_settings(self, screen: Screen, pictures: Pictures) -> None:
        pictures.rest()

        pictures.around(guide_picture(PAGE, "general-settings"), TAG_MAIN_CONFIG_PANEL)

    def picture_advanced_settings(self, screen: Screen, pictures: Pictures) -> None:
        screen.menu.choose(
            MenuElements.GROUP_VIEW,
            MenuElements.ITEM_VIEW_SHOW_ADVANCED_SETTINGS,
        )
        screen.expect(
            screen.main.advanced.is_shown,
            bool,
            description="the Advanced settings card",
        )
        pictures.rest()

        pictures.around(guide_picture(PAGE, "advanced-settings"), TAG_MAIN_ADVANCED_PANEL)
