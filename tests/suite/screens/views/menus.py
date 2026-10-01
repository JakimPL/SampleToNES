from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.tags.general import TAG_GLOBAL_WINDOW_MAIN
from sampletones_application.utils.callbacks.queue import CallbackQueue
from tests.suite.screens.dearpygui.bridge import Bridge
from tests.suite.screens.dearpygui.items import MENU_ITEM_TYPE, MENU_TYPE, find_labelled
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
        group_label = self._label(group)
        item_label = self._label(item)

        def press() -> None:
            menu = find_labelled(
                TAG_GLOBAL_WINDOW_MAIN,
                group_label,
                item_type=MENU_TYPE,
            )
            entry = find_labelled(
                menu,
                item_label,
                item_type=MENU_ITEM_TYPE,
            )
            invoke(entry, CallbackQueue.run)

        self._bridge.ask(press)

    def _label(self, element: MenuElements) -> str:
        return self._language[
            Page.GLOBAL,
            Panel.MENU,
            TextType.LABEL,
            element,
        ]
