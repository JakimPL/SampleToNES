from typing import Final

from assets.pictures.paths import guide_picture
from assets.pictures.writer import Pictures
from automation.screen import Screen
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
    TAG_GLOBAL_PANEL_PLAYER,
    TAG_GLOBAL_TAB_INSTRUCTIONS,
)
from sampletones_application.tags.player import SUF_PLAYER_STOP

PAGE: Final[str] = "interface"
STOP_BUTTON: Final[str] = compose_tag(TAG_GLOBAL_PANEL_PLAYER, SUF_PLAYER_STOP)


class InterfaceScenes:
    """The strip along the top of the window: the menus, the play controls beside them, and the four tabs."""

    def picture_tabs(self, screen: Screen, pictures: Pictures) -> None:
        pictures.rest()
        pictures.corner(
            guide_picture(PAGE, "tabs"),
            STOP_BUTTON,
            TAG_GLOBAL_TAB_INSTRUCTIONS,
        )
