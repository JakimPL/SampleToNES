from typing import Final, List

from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_application.tags.general import TAG_GLOBAL_MENU_ITEM_PLAYBACK_PLAY, TAG_GLOBAL_MENU_ITEM_PLAYBACK_STOP
from sampletones_application.tags.sequencer import TAG_SEQUENCER_VOICES_TABLE
from tests.suite.screens.dearpygui.bridge import Bridge
from tests.suite.screens.dearpygui.items import read_item, read_label, read_table
from tests.suite.screens.views.menus import MenuBar

NAME_COLUMN: Final[int] = 2
CELL_CONTENT: Final[int] = 0


class Voices:
    """The Voices card of the Sequencer: one row per voice of the project, its number and its name."""

    def __init__(self, bridge: Bridge) -> None:
        self._bridge = bridge

    def names(self) -> List[str]:
        """The names the rows show, top to bottom."""

        def read() -> List[str]:
            return [read_label(row[NAME_COLUMN][CELL_CONTENT]) for row in read_table(TAG_SEQUENCER_VOICES_TABLE)]

        return self._bridge.ask(read)


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
        menu: MenuBar,
    ) -> None:
        self.voices = Voices(bridge)
        self.playback = Playback(bridge, menu)
