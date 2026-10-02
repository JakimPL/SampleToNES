from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
    SUF_BUTTON,
    TAG_GLOBAL_DIALOG_PROJECT_OPEN,
    TAG_GLOBAL_DIALOG_PROJECT_SAVED,
    TAG_GLOBAL_DIALOG_PROJECT_UNSAVED,
)
from sampletones_application.tags.settings import (
    TAG_SETTINGS_PROPERTIES_BUTTON_OK,
    TAG_SETTINGS_PROPERTIES_INPUT_TITLE,
    TAG_SETTINGS_PROPERTIES_WINDOW,
)
from tests.suite.screens.dearpygui.bridge import Bridge
from tests.suite.screens.dearpygui.hand import Hand
from tests.suite.screens.dearpygui.items import read_item, read_value
from tests.suite.screens.views.menus import MenuBar
from tests.suite.screens.views.prompts import Prompt


class ProjectProperties:
    """The Project properties dialog: the title, the author and the highlights a project carries."""

    def __init__(
        self,
        bridge: Bridge,
        hand: Hand,
        menu: MenuBar,
    ) -> None:
        self._bridge = bridge
        self._hand = hand
        self._menu = menu

    def open(self) -> None:
        """Opens the dialog from File ▸ Project properties."""
        self._menu.choose(MenuElements.GROUP_FILE, MenuElements.ITEM_FILE_PROJECT_PROPERTIES)

    def is_shown(self) -> bool:
        return self._bridge.ask(lambda: read_item(TAG_SETTINGS_PROPERTIES_WINDOW)).shown

    def title(self) -> str:
        return str(self._bridge.ask(lambda: read_value(TAG_SETTINGS_PROPERTIES_INPUT_TITLE)))

    def retitle(self, title: str) -> None:
        """Types ``title`` over the title the field holds."""
        self._hand.replace_text(TAG_SETTINGS_PROPERTIES_INPUT_TITLE, title)

    def confirm(self) -> None:
        self._hand.click(compose_tag(TAG_SETTINGS_PROPERTIES_BUTTON_OK, SUF_BUTTON))


class Project:
    """The project as the File menu reaches it, with the questions the application asks about it."""

    def __init__(
        self,
        bridge: Bridge,
        hand: Hand,
        menu: MenuBar,
    ) -> None:
        self._menu = menu
        self.properties = ProjectProperties(bridge, hand, menu)
        self.unsaved_prompt = Prompt(bridge, hand, TAG_GLOBAL_DIALOG_PROJECT_UNSAVED)
        self.saved_notice = Prompt(bridge, hand, TAG_GLOBAL_DIALOG_PROJECT_SAVED)
        self.replace_prompt = Prompt(bridge, hand, TAG_GLOBAL_DIALOG_PROJECT_OPEN)

    def open(self) -> None:
        """Chooses File ▸ Open project, which asks for a file."""
        self._menu.choose(MenuElements.GROUP_FILE, MenuElements.ITEM_FILE_OPEN_PROJECT)

    def create(self) -> None:
        """Starts a new project from File ▸ New project."""
        self._menu.choose(MenuElements.GROUP_FILE, MenuElements.ITEM_FILE_NEW_PROJECT)

    def close(self) -> None:
        """Closes the project from File ▸ Close project."""
        self._menu.choose(MenuElements.GROUP_FILE, MenuElements.ITEM_FILE_CLOSE_PROJECT)

    def save_as(self) -> None:
        """Saves the project from File ▸ Save project as, which asks where."""
        self._menu.choose(MenuElements.GROUP_FILE, MenuElements.ITEM_FILE_SAVE_PROJECT_AS)
