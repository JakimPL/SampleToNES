from typing import Tuple

import dearpygui.dearpygui as dpg

from automation.dearpygui.bridge import Bridge
from automation.dearpygui.hand import Hand
from automation.dearpygui.items.reading import read_item, read_value
from automation.dearpygui.semantic import choose
from automation.views.menus import MenuBar
from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import SUF_BUTTON
from sampletones_application.tags.settings import (
    TAG_SETTINGS_MIDI_BUTTON_CANCEL,
    TAG_SETTINGS_MIDI_BUTTON_OK,
    TAG_SETTINGS_MIDI_BUTTON_REFRESH,
    TAG_SETTINGS_MIDI_COMBO_PORT,
    TAG_SETTINGS_MIDI_TEXT_LAST_KEY,
    TAG_SETTINGS_MIDI_TEXT_MESSAGE,
    TAG_SETTINGS_MIDI_TEXT_UNAVAILABLE,
    TAG_SETTINGS_MIDI_TEXT_VELOCITY,
    TAG_SETTINGS_MIDI_WINDOW,
)
from sampletones_application.utils.callbacks.queue import CallbackQueue

ITEMS = "items"


class MidiSettings:
    """The MIDI settings dialog: the input list, Refresh, the key played last with its velocity, OK and Cancel."""

    def __init__(self, bridge: Bridge, hand: Hand, menu: MenuBar) -> None:
        self._bridge = bridge
        self._hand = hand
        self._menu = menu

    def open(self) -> None:
        """Opens the dialog through Playback ▸ MIDI settings..."""
        self._menu.choose(
            MenuElements.GROUP_PLAYBACK,
            MenuElements.ITEM_PLAYBACK_MIDI_SETTINGS,
        )

    def is_shown(self) -> bool:
        return self._bridge.ask(lambda: read_item(TAG_SETTINGS_MIDI_WINDOW)).shown

    def inputs(self) -> Tuple[str, ...]:
        """The entries the input list offers, in order."""
        return tuple(
            str(entry)
            for entry in self._bridge.ask(lambda: dpg.get_item_configuration(TAG_SETTINGS_MIDI_COMBO_PORT))[ITEMS]
        )

    def input(self) -> str:
        """The entry the input list names."""
        return str(self._bridge.ask(lambda: read_value(TAG_SETTINGS_MIDI_COMBO_PORT)))

    def choose_input(self, name: str) -> None:
        """Picks ``name`` in the input list, which reads that keyboard at once."""
        self._bridge.ask(lambda: choose(TAG_SETTINGS_MIDI_COMBO_PORT, name, CallbackQueue.run))

    def last_key(self) -> Tuple[str, str]:
        """The name of the key played last and its velocity, as the dialog reads them."""
        return self._bridge.ask(
            lambda: (
                str(read_value(TAG_SETTINGS_MIDI_TEXT_LAST_KEY)),
                str(read_value(TAG_SETTINGS_MIDI_TEXT_VELOCITY)),
            )
        )

    def message(self) -> str:
        """What the line above the key played last reads: how to try the keyboard, or why it failed to open."""
        return str(self._bridge.ask(lambda: read_value(TAG_SETTINGS_MIDI_TEXT_MESSAGE)))

    def unavailable_line(self) -> str:
        """What the line telling of a machine with no MIDI library reads."""
        return str(self._bridge.ask(lambda: read_value(TAG_SETTINGS_MIDI_TEXT_UNAVAILABLE)))

    def refresh(self) -> None:
        self._hand.click(compose_tag(TAG_SETTINGS_MIDI_BUTTON_REFRESH, SUF_BUTTON))

    def confirm(self) -> None:
        """Presses OK, which keeps the keyboard and the velocity setting and closes the dialog."""
        self._hand.click(compose_tag(TAG_SETTINGS_MIDI_BUTTON_OK, SUF_BUTTON))

    def cancel(self) -> None:
        """Presses Cancel, which reads again the keyboard the dialog opened with and closes it."""
        self._hand.click(compose_tag(TAG_SETTINGS_MIDI_BUTTON_CANCEL, SUF_BUTTON))
