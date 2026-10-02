from typing import Final, List, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_application.tags.general import (
    TAG_GLOBAL_DIALOG_INSTRUMENT_IMPORTED,
    TAG_GLOBAL_DIALOG_NO_PROJECT_OPEN,
    TAG_GLOBAL_MENU_ITEM_PLAYBACK_PLAY,
    TAG_GLOBAL_MENU_ITEM_PLAYBACK_STOP,
)
from sampletones_application.tags.sequencer import (
    TAG_SEQUENCER_BROWSER_TREE,
    TAG_SEQUENCER_MODULE_DIALOG_NES_FREQUENCY,
    TAG_SEQUENCER_MODULE_INPUT_NES_FREQUENCY,
    TAG_SEQUENCER_ORDER_TABLE,
    TAG_SEQUENCER_VOICES_BUTTON_NEW_INSTRUMENT,
    TAG_SEQUENCER_VOICES_DIALOG_REMOVE,
    TAG_SEQUENCER_VOICES_PANEL,
    TAG_SEQUENCER_VOICES_TABLE,
    TAG_SEQUENCER_VOICES_WINDOW,
)
from sampletones_core.constants.enums import ChannelName
from tests.suite.screens.dearpygui.bridge import Bridge
from tests.suite.screens.dearpygui.geometry import Point
from tests.suite.screens.dearpygui.hand import Hand
from tests.suite.screens.dearpygui.items import Item, read_item, read_label, read_region_view, read_table
from tests.suite.screens.dearpygui.keys import IMGUI_ENTER
from tests.suite.screens.views.browsers import FileTree
from tests.suite.screens.views.history import History
from tests.suite.screens.views.main import Card
from tests.suite.screens.views.menus import MenuBar
from tests.suite.screens.views.notices import Notice
from tests.suite.screens.views.prompts import Prompt
from tests.suite.screens.views.tracker import Tracker

NAME_COLUMN: Final[int] = 2
KIND_COLUMN: Final[int] = 0
COLOR: Final[str] = "color"
MASTER_ORDER_ROW: Final[int] = 0
FIRST_CHANNEL_ORDER_ROW: Final[int] = 2
ORDER_LABEL_CELLS: Final[int] = 1
CELL_CONTENT: Final[int] = 0
CLEAR_OF_THE_EDGE: Final[int] = 12


class Voices:
    """The Voices card of the Sequencer: one row per voice of the project, its number and its name."""

    def __init__(
        self,
        bridge: Bridge,
        hand: Hand,
    ) -> None:
        self._bridge = bridge
        self._hand = hand
        self.remove_prompt = Prompt(bridge, hand, TAG_SEQUENCER_VOICES_DIALOG_REMOVE)
        self.no_project_notice = Notice(bridge, hand, TAG_GLOBAL_DIALOG_NO_PROJECT_OPEN)
        self.imported_notice = Notice(bridge, hand, TAG_GLOBAL_DIALOG_INSTRUMENT_IMPORTED)
        self.card = Card(bridge, hand, TAG_SEQUENCER_VOICES_PANEL)

    def kind_color(self, name: str) -> Tuple[float, ...]:
        """The color of the mark naming the kind of the voice ``name``."""

        def read() -> Tuple[float, ...]:
            row = next(
                row
                for row in read_table(TAG_SEQUENCER_VOICES_TABLE)
                if read_label(row[NAME_COLUMN][CELL_CONTENT]) == name
            )
            return tuple(float(part) for part in dpg.get_item_configuration(row[KIND_COLUMN][CELL_CONTENT])[COLOR])

        return self._bridge.ask(read)

    def pick(self, row: Item) -> None:
        """Clicks ``row``, which picks its voice."""
        self._hand.scroll_into_view(row)
        self._hand.click(row)

    def is_picked(self, position: int) -> bool:
        """Whether the row at ``position`` stands picked."""
        return bool(self._bridge.ask(lambda: dpg.is_table_row_highlighted(TAG_SEQUENCER_VOICES_TABLE, position)))

    def new_instrument(self) -> None:
        """Clicks New instrument above the list."""
        self._hand.scroll_into_view(TAG_SEQUENCER_VOICES_BUTTON_NEW_INSTRUMENT)
        self._hand.click(TAG_SEQUENCER_VOICES_BUTTON_NEW_INSTRUMENT)

    def names(self) -> List[str]:
        """The names the rows show, top to bottom."""

        def read() -> List[str]:
            return [read_label(name) for name in _names()]

        return self._bridge.ask(read)

    def row(self, name: str) -> Optional[Item]:
        """The name cell of the first row reading ``name``, if one is drawn."""
        return self._bridge.ask(lambda: next((item for item in _names() if read_label(item) == name), None))

    def edit(self, row: Item) -> None:
        """Double-clicks ``row``, which opens its voice on the Reconstructions tab."""
        self._hand.scroll_into_view(row)
        self._hand.double_click(row)

    def right_click(self, row: Item) -> None:
        """Clicks ``row`` with the right button, which opens its menu."""
        self._hand.scroll_into_view(row)
        self._hand.right_click(row)

    def right_click_below_the_rows(self) -> None:
        """Clicks the empty foot of the list with the right button, which opens the list's own menu."""
        view = self._bridge.ask(lambda: read_region_view(TAG_SEQUENCER_VOICES_WINDOW))
        if view is None:
            raise LookupError("The list of voices stands nowhere")

        self._hand.right_click_at(Point(x=view.center.x, y=round(view.y + view.height) - CLEAR_OF_THE_EDGE))


class Playback:
    """Song playback as the Playback menu offers it: Play, which reads Pause while a song plays, and Stop."""

    def __init__(
        self,
        bridge: Bridge,
        menu: MenuBar,
    ) -> None:
        self._bridge = bridge
        self._menu = menu

    def play(self) -> None:
        """Chooses Playback ▸ Play."""
        self._menu.choose(MenuElements.GROUP_PLAYBACK, MenuElements.ITEM_PLAYBACK_PLAY)

    def stop(self) -> None:
        """Chooses Playback ▸ Stop."""
        self._menu.choose(MenuElements.GROUP_PLAYBACK, MenuElements.ITEM_PLAYBACK_STOP)

    def play_entry(self) -> str:
        """What the first entry of the Playback menu reads: Play while stopped, Pause while a song plays."""
        return self._bridge.ask(lambda: read_label(TAG_GLOBAL_MENU_ITEM_PLAYBACK_PLAY))

    def can_stop(self) -> bool:
        """Whether Playback ▸ Stop answers, which it does while something plays."""
        return self._bridge.ask(lambda: read_item(TAG_GLOBAL_MENU_ITEM_PLAYBACK_STOP)).enabled


class OrderTable:
    """The order table: a row per channel under the Master row, a column per frame of the song."""

    def __init__(
        self,
        bridge: Bridge,
        hand: Hand,
    ) -> None:
        self._bridge = bridge
        self._hand = hand

    def label(self, channel: Optional[ChannelName], position: int) -> str:
        """What the entry of ``channel`` at frame ``position`` reads, the Master row's for ``None``."""
        return self._bridge.ask(lambda: read_label(_order_entry(channel, position)))

    def positions(self) -> int:
        """How many frames the song orders."""
        return self._bridge.ask(
            lambda: len(read_table(TAG_SEQUENCER_ORDER_TABLE)[MASTER_ORDER_ROW]) - ORDER_LABEL_CELLS
        )

    def click(self, channel: Optional[ChannelName], position: int) -> None:
        entry = self._bridge.ask(lambda: _order_entry(channel, position))
        self._hand.scroll_into_view(entry)
        self._hand.click(entry)


class ModuleOptions:
    """The module options card: the song's NES frequency, rows, tempo and speed."""

    def __init__(
        self,
        bridge: Bridge,
        hand: Hand,
    ) -> None:
        self._bridge = bridge
        self._hand = hand
        self.retune_prompt = Prompt(bridge, hand, TAG_SEQUENCER_MODULE_DIALOG_NES_FREQUENCY)

    def nes_frequency(self) -> int:
        return int(self._bridge.ask(lambda: dpg.get_value(TAG_SEQUENCER_MODULE_INPUT_NES_FREQUENCY)))

    def retype_nes_frequency(self, frequency: int) -> None:
        """Types ``frequency`` over the NES frequency field and presses Enter, which commits it."""
        self._hand.scroll_into_view(TAG_SEQUENCER_MODULE_INPUT_NES_FREQUENCY)
        self._hand.replace_text(TAG_SEQUENCER_MODULE_INPUT_NES_FREQUENCY, str(frequency))
        self._hand.press_key(IMGUI_ENTER, modifiers=[])


class Sequencer:
    """The Sequencer tab: the tracker, the voices, the history, and song playback."""

    def __init__(
        self,
        bridge: Bridge,
        hand: Hand,
        menu: MenuBar,
    ) -> None:
        self.voices = Voices(bridge, hand)
        self.playback = Playback(bridge, menu)
        self.tracker = Tracker(bridge, hand)
        self.history = History(bridge, hand)
        self.browser = FileTree(bridge, hand, TAG_SEQUENCER_BROWSER_TREE)
        self.order = OrderTable(bridge, hand)
        self.module = ModuleOptions(bridge, hand)


def _names() -> List[Item]:
    """The name cell of every voice row, top to bottom. Runs on the render thread."""
    return [row[NAME_COLUMN][CELL_CONTENT] for row in read_table(TAG_SEQUENCER_VOICES_TABLE) if len(row) > NAME_COLUMN]


def _order_entry(channel: Optional[ChannelName], position: int) -> Item:
    """The entry of ``channel`` at frame ``position`` in the order table. Runs on the render thread."""
    row = MASTER_ORDER_ROW if channel is None else FIRST_CHANNEL_ORDER_ROW + ChannelName.items().index(channel)
    entry: Item = read_table(TAG_SEQUENCER_ORDER_TABLE)[row][ORDER_LABEL_CELLS + position][CELL_CONTENT]
    return entry
