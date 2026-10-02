from pathlib import Path

from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
    SUF_GROUP,
    SUF_TEXT,
    SUF_TOOLTIP,
    TAG_GLOBAL_DIALOG_EXIT_CONFIRMATION,
    TAG_GLOBAL_DIALOG_RECONSTRUCTION_REPLACED,
    TAG_GLOBAL_DIALOG_RECONSTRUCTION_SAVED,
)
from sampletones_application.tags.graphs import SUF_GRAPH_RAW_DATA
from sampletones_application.tags.reconstructions import (
    TAG_RECONSTRUCTIONS_BROWSER_DIALOG_REMOVE_RECONSTRUCTION_CONFIRMATION,
    TAG_RECONSTRUCTIONS_BROWSER_TREE,
    TAG_RECONSTRUCTIONS_INSTRUMENTS_RADIO_AUDITION,
    TAG_RECONSTRUCTIONS_INSTRUMENTS_TABS_BAR,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_INPUT_NES_FREQUENCY,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_PATH_RECONSTRUCTION_FILE,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_TOOLTIP_NES_FREQUENCY_LOCKED,
)
from sampletones_core.constants.enums import ChannelName, FeatureKey
from tests.suite.screens.dearpygui.bridge import Bridge
from tests.suite.screens.dearpygui.hand import Hand
from tests.suite.screens.dearpygui.items import read_item, read_texts, read_value
from tests.suite.screens.dearpygui.keys import IMGUI_ENTER
from tests.suite.screens.views.browsers import FileTree
from tests.suite.screens.views.menus import MenuBar
from tests.suite.screens.views.prompts import Prompt

OPEN_FILE_TOOLTIP = compose_tag(TAG_RECONSTRUCTIONS_RECONSTRUCTION_PATH_RECONSTRUCTION_FILE, SUF_TOOLTIP)


class Reconstructions:
    """The Reconstructions tab: the browser of saved reconstructions, and the one open beside it.

    Every question about unsaved changes to the open reconstruction stands under one kind of
    prompt, whichever gesture asked it, so ``unsaved_prompt`` reads any of them, and its title and
    words tell which.
    """

    def __init__(
        self,
        bridge: Bridge,
        hand: Hand,
        menu: MenuBar,
    ) -> None:
        self._bridge = bridge
        self._hand = hand
        self._menu = menu
        self.browser = FileTree(bridge, hand, TAG_RECONSTRUCTIONS_BROWSER_TREE)
        self.unsaved_prompt = Prompt(bridge, hand, TAG_GLOBAL_DIALOG_EXIT_CONFIRMATION)
        self.replaced_prompt = Prompt(bridge, hand, TAG_GLOBAL_DIALOG_RECONSTRUCTION_REPLACED)
        self.remove_prompt = Prompt(bridge, hand, TAG_RECONSTRUCTIONS_BROWSER_DIALOG_REMOVE_RECONSTRUCTION_CONFIRMATION)
        self.saved_notice = Prompt(bridge, hand, TAG_GLOBAL_DIALOG_RECONSTRUCTION_SAVED)

    def open_from_menu(self) -> None:
        """Chooses Reconstruction ▸ Open, which asks for a file."""
        self._menu.choose(MenuElements.GROUP_RECONSTRUCTION, MenuElements.ITEM_RECONSTRUCTION_OPEN)

    def close_from_menu(self) -> None:
        """Chooses Reconstruction ▸ Close."""
        self._menu.choose(MenuElements.GROUP_RECONSTRUCTION, MenuElements.ITEM_RECONSTRUCTION_CLOSE)

    def save_from_menu(self) -> None:
        """Chooses Reconstruction ▸ Save."""
        self._menu.choose(MenuElements.GROUP_RECONSTRUCTION, MenuElements.ITEM_RECONSTRUCTION_SAVE)

    def can_close(self) -> bool:
        """Whether Reconstruction ▸ Close answers."""
        return self._menu.is_enabled(MenuElements.GROUP_RECONSTRUCTION, MenuElements.ITEM_RECONSTRUCTION_CLOSE)

    def can_save(self) -> bool:
        """Whether Reconstruction ▸ Save answers."""
        return self._menu.is_enabled(MenuElements.GROUP_RECONSTRUCTION, MenuElements.ITEM_RECONSTRUCTION_SAVE)

    def open_file(self) -> str:
        """The whole path of the open reconstruction's file, as the hover over its shortened path shows it.

        Nothing open, or a reconstruction holding no file, reads as the status the line shows instead.
        """
        return " ".join(self._bridge.ask(lambda: read_texts(OPEN_FILE_TOOLTIP)))

    def shows_open(self, path: Path) -> bool:
        """Whether the reconstruction open is the one stored at ``path``."""
        return self.open_file() == str(path.absolute())

    def file_line(self) -> str:
        """What the Reconstruction file line of Source settings shows: a shortened path, or a status."""
        return str(self._bridge.ask(lambda: read_value(TAG_RECONSTRUCTIONS_RECONSTRUCTION_PATH_RECONSTRUCTION_FILE)))

    def can_retune(self) -> bool:
        """Whether the NES frequency field takes a new rate."""
        return self._bridge.ask(lambda: read_item(TAG_RECONSTRUCTIONS_RECONSTRUCTION_INPUT_NES_FREQUENCY)).enabled

    def retune_lock_explained(self) -> bool:
        """Whether hovering the NES frequency field explains why it takes no new rate."""
        return self._bridge.ask(
            lambda: read_item(TAG_RECONSTRUCTIONS_RECONSTRUCTION_TOOLTIP_NES_FREQUENCY_LOCKED)
        ).shown

    def retune_lock_words(self) -> str:
        """What hovering the locked NES frequency field says."""
        return " ".join(
            self._bridge.ask(lambda: read_texts(TAG_RECONSTRUCTIONS_RECONSTRUCTION_TOOLTIP_NES_FREQUENCY_LOCKED))
        )

    def offers_audition(self) -> bool:
        """Whether the Audition switch stands, which it does while a hand-written instrument is open."""
        return self._bridge.ask(
            lambda: read_item(compose_tag(TAG_RECONSTRUCTIONS_INSTRUMENTS_RADIO_AUDITION, SUF_GROUP))
        ).shown

    def envelope(
        self,
        channel: ChannelName,
        feature: FeatureKey,
    ) -> str:
        """The sequence the field under ``channel``'s ``feature`` graph holds, as the reader would edit it."""
        return str(self._bridge.ask(lambda: read_value(_envelope_field(channel, feature))))

    def type_envelope(
        self,
        channel: ChannelName,
        feature: FeatureKey,
        sequence: str,
    ) -> None:
        """Brings ``channel``'s tab forward, types ``sequence`` over its ``feature`` field and presses Enter."""
        self._hand.click(compose_tag(TAG_RECONSTRUCTIONS_INSTRUMENTS_TABS_BAR, channel))
        field = _envelope_field(channel, feature)
        self._hand.scroll_into_view(field)
        self._hand.replace_text(field, sequence)
        self._hand.press_key(IMGUI_ENTER, modifiers=[])


def _envelope_field(channel: ChannelName, feature: FeatureKey) -> str:
    return compose_tag(TAG_RECONSTRUCTIONS_INSTRUMENTS_TABS_BAR, channel, feature, SUF_GRAPH_RAW_DATA, SUF_TEXT)
