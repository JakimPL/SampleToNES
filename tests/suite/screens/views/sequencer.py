from typing import Final, List, Optional

from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_application.tags.general import TAG_GLOBAL_MENU_ITEM_PLAYBACK_PLAY, TAG_GLOBAL_MENU_ITEM_PLAYBACK_STOP
from sampletones_application.tags.sequencer import TAG_SEQUENCER_VOICES_DIALOG_REMOVE, TAG_SEQUENCER_VOICES_TABLE
from tests.suite.screens.dearpygui.bridge import Bridge
from tests.suite.screens.dearpygui.hand import Hand
from tests.suite.screens.dearpygui.items import Item, read_item, read_label, read_table
from tests.suite.screens.views.menus import MenuBar
from tests.suite.screens.views.prompts import Prompt

NAME_COLUMN: Final[int] = 2
CELL_CONTENT: Final[int] = 0


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


class Sequencer:
    """The Sequencer tab, as far as scenarios read it."""

    def __init__(
        self,
        bridge: Bridge,
        hand: Hand,
        menu: MenuBar,
    ) -> None:
        self.voices = Voices(bridge, hand)
        self.playback = Playback(bridge, menu)


def _names() -> List[Item]:
    """The name cell of every voice row, top to bottom. Runs on the render thread."""
    return [row[NAME_COLUMN][CELL_CONTENT] for row in read_table(TAG_SEQUENCER_VOICES_TABLE)]
