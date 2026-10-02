from pathlib import Path

from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import SUF_TOOLTIP
from sampletones_application.tags.reconstructions import (
    TAG_RECONSTRUCTIONS_BROWSER_TREE,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_PATH_RECONSTRUCTION_FILE,
)
from tests.suite.screens.dearpygui.bridge import Bridge
from tests.suite.screens.dearpygui.hand import Hand
from tests.suite.screens.dearpygui.items import read_texts
from tests.suite.screens.views.browsers import FileTree
from tests.suite.screens.views.menus import MenuBar

OPEN_FILE_TOOLTIP = compose_tag(TAG_RECONSTRUCTIONS_RECONSTRUCTION_PATH_RECONSTRUCTION_FILE, SUF_TOOLTIP)


class Reconstructions:
    """The Reconstructions tab: the browser of saved reconstructions, and the one open beside it."""

    def __init__(
        self,
        bridge: Bridge,
        hand: Hand,
        menu: MenuBar,
    ) -> None:
        self._bridge = bridge
        self._menu = menu
        self.browser = FileTree(bridge, hand, TAG_RECONSTRUCTIONS_BROWSER_TREE)

    def open_from_menu(self) -> None:
        """Chooses Reconstruction ▸ Open, which asks for a file."""
        self._menu.choose(MenuElements.GROUP_RECONSTRUCTION, MenuElements.ITEM_RECONSTRUCTION_OPEN)

    def open_file(self) -> str:
        """The whole path of the open reconstruction's file, as the hover over its shortened path shows it.

        Nothing open, or a reconstruction holding no file, reads as the status the line shows instead.
        """
        return " ".join(self._bridge.ask(lambda: read_texts(OPEN_FILE_TOOLTIP)))

    def shows_open(self, path: Path) -> bool:
        """Whether the reconstruction open is the one stored at ``path``."""
        return self.open_file() == str(path.absolute())
