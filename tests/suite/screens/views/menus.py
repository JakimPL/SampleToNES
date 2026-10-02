from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.tags.general import TAG_GLOBAL_WINDOW_MAIN
from sampletones_application.utils.callbacks.queue import CallbackQueue
from tests.suite.screens.dearpygui.bridge import Bridge
from tests.suite.screens.dearpygui.items import MENU_ITEM_TYPE, MENU_TYPE, Item, find_labelled, read_item
from tests.suite.screens.dearpygui.semantic import invoke


class MenuBar:
    """The menu bar along the top of the window, read by the words its menus show.

    A menu and its entry are found by their labels, which the language file gives, so a scenario
    names an entry the way a user reads it. DearPyGui reports a menu entry's position alone, so
    choosing one runs its callback the way a click on it does.
    """

    def __init__(
        self,
        bridge: Bridge,
        language: LanguageManager,
    ) -> None:
        self._bridge = bridge
        self._language = language

    def choose(
        self,
        group: MenuElements,
        item: MenuElements,
    ) -> None:
        """Chooses the entry ``item`` of the menu ``group``."""
        self._bridge.ask(lambda: invoke(self._entry(group, item), CallbackQueue.run))

    def is_enabled(
        self,
        group: MenuElements,
        item: MenuElements,
    ) -> bool:
        """Whether the entry ``item`` of the menu ``group`` answers a press."""
        return self._bridge.ask(lambda: read_item(self._entry(group, item)).enabled)

    def _entry(
        self,
        group: MenuElements,
        item: MenuElements,
    ) -> Item:
        """The entry ``item`` of the menu ``group``. Runs on the render thread."""
        menu = find_labelled(
            TAG_GLOBAL_WINDOW_MAIN,
            self._label(group),
            item_type=MENU_TYPE,
        )
        return find_labelled(
            menu,
            self._label(item),
            item_type=MENU_ITEM_TYPE,
        )

    def _label(self, element: MenuElements) -> str:
        return self._language[
            Page.GLOBAL,
            Panel.MENU,
            TextType.LABEL,
            element,
        ]
