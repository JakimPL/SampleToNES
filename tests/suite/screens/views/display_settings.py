from typing import Final, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import SUF_BUTTON
from sampletones_application.tags.settings import (
    TAG_SETTINGS_DISPLAY_BUTTON_CANCEL,
    TAG_SETTINGS_DISPLAY_BUTTON_KEEP,
    TAG_SETTINGS_DISPLAY_BUTTON_OK,
    TAG_SETTINGS_DISPLAY_BUTTON_REVERT,
    TAG_SETTINGS_DISPLAY_CHECKBOX_BORDERLESS,
    TAG_SETTINGS_DISPLAY_CHECKBOX_SHOW_FRAME_RATE,
    TAG_SETTINGS_DISPLAY_CHECKBOX_VSYNC,
    TAG_SETTINGS_DISPLAY_COMBO_PALETTE,
    TAG_SETTINGS_DISPLAY_COMBO_RESOLUTION,
    TAG_SETTINGS_DISPLAY_DIALOG_DISCARD,
    TAG_SETTINGS_DISPLAY_WINDOW,
    TAG_SETTINGS_DISPLAY_WINDOW_COUNTDOWN,
)
from sampletones_application.utils.callbacks.queue import CallbackQueue
from tests.suite.screens.dearpygui.bridge import Bridge
from tests.suite.screens.dearpygui.hand import Hand
from tests.suite.screens.dearpygui.items.reading import read_item, read_value
from tests.suite.screens.dearpygui.semantic import choose
from tests.suite.screens.views.menus import MenuBar
from tests.suite.screens.views.prompts import Prompt

ITEMS: Final[str] = "items"


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
        """Whether the dialog stands on the screen."""
        return self._bridge.ask(lambda: read_item(TAG_SETTINGS_DISPLAY_WINDOW)).shown

    def resolution(self) -> str:
        """The window size the Resolution list names."""
        return str(self._bridge.ask(lambda: read_value(TAG_SETTINGS_DISPLAY_COMBO_RESOLUTION)))

    def resolutions(self) -> Tuple[str, ...]:
        """The window sizes the Resolution list offers, in order."""
        return tuple(
            str(item)
            for item in self._bridge.ask(lambda: dpg.get_item_configuration(TAG_SETTINGS_DISPLAY_COMBO_RESOLUTION))[
                ITEMS
            ]
        )

    def choose_resolution(self, label: str) -> None:
        """Picks the window size reading ``label`` in the Resolution list.

        The window resizes and the countdown starts.
        """
        self._bridge.ask(lambda: choose(TAG_SETTINGS_DISPLAY_COMBO_RESOLUTION, label, CallbackQueue.run))

    def palette(self) -> str:
        """The palette the Palette list names."""
        return str(self._bridge.ask(lambda: read_value(TAG_SETTINGS_DISPLAY_COMBO_PALETTE)))

    def choose_palette(self, name: str) -> None:
        """Picks the palette ``name`` in the Palette list, which repaints the interface at once."""
        self._bridge.ask(lambda: choose(TAG_SETTINGS_DISPLAY_COMBO_PALETTE, name, CallbackQueue.run))

    def vsync(self) -> bool:
        """Whether the vertical sync box stands ticked."""
        return bool(self._bridge.ask(lambda: read_value(TAG_SETTINGS_DISPLAY_CHECKBOX_VSYNC)))

    def toggle_vsync(self) -> None:
        """Clicks the vertical sync box, which ticks it or lets it go."""
        self._hand.click(TAG_SETTINGS_DISPLAY_CHECKBOX_VSYNC)

    def frame_rate_shown(self) -> bool:
        """Whether the Show frame rate box stands ticked."""
        return bool(self._bridge.ask(lambda: read_value(TAG_SETTINGS_DISPLAY_CHECKBOX_SHOW_FRAME_RATE)))

    def toggle_frame_rate(self) -> None:
        """Clicks the Show frame rate box, which puts the reading on the menu bar or takes it off at once."""
        self._hand.click(TAG_SETTINGS_DISPLAY_CHECKBOX_SHOW_FRAME_RATE)

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
        """Presses Cancel, which drops the changes and closes the dialog."""
        self._hand.click(compose_tag(TAG_SETTINGS_DISPLAY_BUTTON_CANCEL, SUF_BUTTON))

    def confirm(self) -> None:
        """Presses OK, which keeps the changes and closes the dialog."""
        self._hand.click(compose_tag(TAG_SETTINGS_DISPLAY_BUTTON_OK, SUF_BUTTON))
