from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import SUF_BUTTON
from sampletones_application.tags.settings import (
    TAG_SETTINGS_DISPLAY_BUTTON_CANCEL,
    TAG_SETTINGS_DISPLAY_BUTTON_KEEP,
    TAG_SETTINGS_DISPLAY_BUTTON_OK,
    TAG_SETTINGS_DISPLAY_BUTTON_REVERT,
    TAG_SETTINGS_DISPLAY_CHECKBOX_BORDERLESS,
    TAG_SETTINGS_DISPLAY_CHECKBOX_VSYNC,
    TAG_SETTINGS_DISPLAY_DIALOG_DISCARD,
    TAG_SETTINGS_DISPLAY_WINDOW,
    TAG_SETTINGS_DISPLAY_WINDOW_COUNTDOWN,
)
from tests.suite.screens.dearpygui.bridge import Bridge
from tests.suite.screens.dearpygui.hand import Hand
from tests.suite.screens.dearpygui.items import read_item, read_value
from tests.suite.screens.views.menus import MenuBar
from tests.suite.screens.views.prompts import Prompt


class DisplaySettings:
    """The Display settings dialog: the window mode, the pacing and the palette, with Cancel and OK."""

    def __init__(
        self,
        bridge: Bridge,
        hand: Hand,
        menu: MenuBar,
    ) -> None:
        self._bridge = bridge
        self._hand = hand
        self._menu = menu
        self.discard_prompt = Prompt(bridge, hand, TAG_SETTINGS_DISPLAY_DIALOG_DISCARD)

    def open(self) -> None:
        """Opens the dialog from View ▸ Display settings."""
        self._menu.choose(MenuElements.GROUP_VIEW, MenuElements.ITEM_VIEW_DISPLAY_SETTINGS)

    def is_shown(self) -> bool:
        return self._bridge.ask(lambda: read_item(TAG_SETTINGS_DISPLAY_WINDOW)).shown

    def vsync(self) -> bool:
        """Whether the vertical sync box stands ticked."""
        return bool(self._bridge.ask(lambda: read_value(TAG_SETTINGS_DISPLAY_CHECKBOX_VSYNC)))

    def toggle_vsync(self) -> None:
        self._hand.click(TAG_SETTINGS_DISPLAY_CHECKBOX_VSYNC)

    def borderless(self) -> bool:
        """Whether the borderless box stands ticked."""
        return bool(self._bridge.ask(lambda: read_value(TAG_SETTINGS_DISPLAY_CHECKBOX_BORDERLESS)))

    def toggle_borderless(self) -> None:
        """Clicks the borderless box, which changes the window mode and starts the countdown."""
        self._hand.click(TAG_SETTINGS_DISPLAY_CHECKBOX_BORDERLESS)

    def countdown_shown(self) -> bool:
        """Whether the countdown asking to keep a new window mode stands."""
        return self._bridge.ask(lambda: read_item(TAG_SETTINGS_DISPLAY_WINDOW_COUNTDOWN)).shown

    def keep(self) -> None:
        """Presses Keep on the countdown."""
        self._hand.click(compose_tag(TAG_SETTINGS_DISPLAY_BUTTON_KEEP, SUF_BUTTON))

    def revert(self) -> None:
        """Presses Revert on the countdown."""
        self._hand.click(compose_tag(TAG_SETTINGS_DISPLAY_BUTTON_REVERT, SUF_BUTTON))

    def cancel(self) -> None:
        self._hand.click(compose_tag(TAG_SETTINGS_DISPLAY_BUTTON_CANCEL, SUF_BUTTON))

    def confirm(self) -> None:
        self._hand.click(compose_tag(TAG_SETTINGS_DISPLAY_BUTTON_OK, SUF_BUTTON))
