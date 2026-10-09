from automation.dearpygui.bridge import Bridge
from automation.dearpygui.hand import Hand
from automation.dearpygui.items.reading import read_item
from automation.dearpygui.items.texts import read_label
from automation.dearpygui.keys import IMGUI_ENTER
from automation.views.menus import MenuBar
from automation.views.prompts import Prompt
from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import SUF_BUTTON
from sampletones_application.tags.settings import (
    PRE_SETTINGS_KEYBINDINGS_ROW,
    SUF_SETTINGS_KEYBINDINGS_ACTION,
    SUF_SETTINGS_KEYBINDINGS_SHORTCUT,
    TAG_SETTINGS_KEYBINDINGS_BUTTON_CANCEL,
    TAG_SETTINGS_KEYBINDINGS_BUTTON_OK,
    TAG_SETTINGS_KEYBINDINGS_DIALOG_REASSIGN,
    TAG_SETTINGS_KEYBINDINGS_INPUT_SHORTCUT,
    TAG_SETTINGS_KEYBINDINGS_WINDOW,
)
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId


class KeyboardSettings:
    """The Keyboard settings dialog: one row per action with the keys it answers to, and Cancel and OK."""

    def __init__(
        self,
        bridge: Bridge,
        hand: Hand,
        menu: MenuBar,
    ) -> None:
        self._bridge = bridge
        self._hand = hand
        self._menu = menu
        self.reassign_prompt = Prompt(bridge, hand, TAG_SETTINGS_KEYBINDINGS_DIALOG_REASSIGN)

    def open(self) -> None:
        """Opens the dialog from View ▸ Keyboard settings."""
        self._menu.choose(MenuElements.GROUP_VIEW, MenuElements.ITEM_VIEW_KEYBOARD_SETTINGS)

    def is_shown(self) -> bool:
        """Whether the dialog stands on the screen."""
        return self._bridge.ask(lambda: read_item(TAG_SETTINGS_KEYBINDINGS_WINDOW)).shown

    def listen_for(self, shortcut_id: ShortcutId) -> None:
        """Clicks the keys of ``shortcut_id``'s row, which listens for the next keys pressed."""
        cell = _shortcut_cell(shortcut_id)
        self._hand.scroll_into_view(cell)
        self._hand.click(cell)

    def write_keys(self, shortcut_id: ShortcutId, text: str) -> None:
        """Picks the row of ``shortcut_id`` by its name, writes ``text`` over the keys in the entry box
        and presses Enter, which gives the action exactly the keys written.
        """
        action = _action_cell(shortcut_id)
        self._hand.scroll_into_view(action)
        self._hand.click(action)
        self._hand.replace_text(TAG_SETTINGS_KEYBINDINGS_INPUT_SHORTCUT, text)
        self._hand.press_key(IMGUI_ENTER, modifiers=[])

    def keys_of(self, shortcut_id: ShortcutId) -> str:
        """What the row of ``shortcut_id`` shows as its keys."""
        return self._bridge.ask(lambda: read_label(_shortcut_cell(shortcut_id)))

    def cancel(self) -> None:
        """Presses Cancel, which drops the keys edited and closes the dialog."""
        self._hand.click(compose_tag(TAG_SETTINGS_KEYBINDINGS_BUTTON_CANCEL, SUF_BUTTON))

    def confirm(self) -> None:
        """Presses OK, which puts the keys edited in force."""
        self._hand.click(compose_tag(TAG_SETTINGS_KEYBINDINGS_BUTTON_OK, SUF_BUTTON))


def _shortcut_cell(shortcut_id: ShortcutId) -> str:
    return compose_tag(
        PRE_SETTINGS_KEYBINDINGS_ROW,
        shortcut_id.value,
        SUF_SETTINGS_KEYBINDINGS_SHORTCUT,
    )


def _action_cell(shortcut_id: ShortcutId) -> str:
    return compose_tag(
        PRE_SETTINGS_KEYBINDINGS_ROW,
        shortcut_id.value,
        SUF_SETTINGS_KEYBINDINGS_ACTION,
    )
