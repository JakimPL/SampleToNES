from pathlib import Path

from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
    SUF_TOOLTIP,
    TAG_GLOBAL_DIALOG_EXIT_CONFIRMATION,
    TAG_GLOBAL_DIALOG_RECONSTRUCTION_REPLACED,
    TAG_GLOBAL_DIALOG_RECONSTRUCTION_SAVED,
)
from sampletones_application.tags.reconstructions import (
    PRE_RECONSTRUCTION_CHANNEL,
    TAG_RECONSTRUCTIONS_BROWSER_DIALOG_REMOVE_RECONSTRUCTION_CONFIRMATION,
    TAG_RECONSTRUCTIONS_BROWSER_TREE,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_INPUT_NES_FREQUENCY,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_PANEL_RECONSTRUCTION_WAVEFORM,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_PATH_RECONSTRUCTION_FILE,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_RADIO_AUDIO_SOURCE,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_TOOLTIP_NES_FREQUENCY_LOCKED,
)
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_core.constants.enums import ChannelName
from tests.suite.screens.dearpygui.bridge import Bridge
from tests.suite.screens.dearpygui.hand import Hand
from tests.suite.screens.dearpygui.items.reading import read_item, read_value
from tests.suite.screens.dearpygui.items.texts import read_texts
from tests.suite.screens.dearpygui.semantic import choose
from tests.suite.screens.views.browsers import FileTree
from tests.suite.screens.views.instruments import Instruments
from tests.suite.screens.views.menus import MenuBar
from tests.suite.screens.views.prompts import Prompt
from tests.suite.screens.views.stems import StemsCard
from tests.suite.screens.views.waveform import Waveform

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
        self.waveform = Waveform(bridge, hand, TAG_RECONSTRUCTIONS_RECONSTRUCTION_PANEL_RECONSTRUCTION_WAVEFORM)
        self.instruments = Instruments(bridge, hand)
        self.stems = StemsCard(bridge, hand)

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

        While nothing is open, or the reconstruction has no file yet, the hover shows the status of the line.
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
        """Whether hovering the NES frequency field shows why the rate is locked."""
        return self._bridge.ask(
            lambda: read_item(TAG_RECONSTRUCTIONS_RECONSTRUCTION_TOOLTIP_NES_FREQUENCY_LOCKED)
        ).shown

    def retune_lock_words(self) -> str:
        """What hovering the locked NES frequency field says."""
        return " ".join(
            self._bridge.ask(lambda: read_texts(TAG_RECONSTRUCTIONS_RECONSTRUCTION_TOOLTIP_NES_FREQUENCY_LOCKED))
        )

    def audio_source(self) -> str:
        """The source the switch above the waveform names: the reconstruction, or the original audio."""
        return str(self._bridge.ask(lambda: read_value(TAG_RECONSTRUCTIONS_RECONSTRUCTION_RADIO_AUDIO_SOURCE)))

    def can_choose_audio_source(self) -> bool:
        """Whether the switch above the waveform answers a press."""
        return self._bridge.ask(lambda: read_item(TAG_RECONSTRUCTIONS_RECONSTRUCTION_RADIO_AUDIO_SOURCE)).enabled

    def choose_audio_source(self, label: str) -> None:
        """Picks the source the switch names ``label``."""
        self._bridge.ask(
            lambda: choose(TAG_RECONSTRUCTIONS_RECONSTRUCTION_RADIO_AUDIO_SOURCE, label, CallbackQueue.run)
        )

    def channel_ticked(self, channel: ChannelName) -> bool:
        """Whether the box of ``channel`` above the waveform stands ticked."""
        return bool(self._bridge.ask(lambda: read_value(_channel_box(channel))))

    def channel_plays(self, channel: ChannelName) -> bool:
        """Whether the box of ``channel`` answers, which it does for a channel the reconstruction plays."""
        return self._bridge.ask(lambda: read_item(_channel_box(channel))).enabled

    def tick_channel(self, channel: ChannelName) -> None:
        """Clicks the box of ``channel`` above the waveform, which flips its tick."""
        self._hand.click(_channel_box(channel))


def _channel_box(channel: ChannelName) -> str:
    return compose_tag(PRE_RECONSTRUCTION_CHANNEL, channel.value)
