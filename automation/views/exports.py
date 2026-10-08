from typing import Tuple

from automation.dearpygui.bridge import Bridge
from automation.dearpygui.hand import Hand
from automation.dearpygui.items.reading import read_item, read_value
from automation.dearpygui.items.texts import read_shown_texts
from automation.dearpygui.semantic import choose
from automation.views.menus import MenuBar
from automation.views.notices import Notice
from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
    SUF_BUTTON,
    TAG_GLOBAL_DIALOG_MODULE_EXPORTED,
    TAG_GLOBAL_DIALOG_PATH_MESSAGE,
)
from sampletones_application.tags.settings import (
    TAG_SETTINGS_EXPORT_BUTTON_CANCEL,
    TAG_SETTINGS_EXPORT_GROUP_STAGES,
    TAG_SETTINGS_EXPORT_WINDOW,
    TAG_SETTINGS_NSF_BUTTON_BROWSE,
    TAG_SETTINGS_NSF_BUTTON_CANCEL,
    TAG_SETTINGS_NSF_BUTTON_EXPORT,
    TAG_SETTINGS_NSF_CHECKBOX_CHANNEL,
    TAG_SETTINGS_NSF_COMBO_REPEAT,
    TAG_SETTINGS_NSF_COMBO_SCHEME,
    TAG_SETTINGS_NSF_INPUT_LOOP_FRAME,
    TAG_SETTINGS_NSF_INPUT_TITLE,
    TAG_SETTINGS_NSF_TEXT_NO_CHANNEL,
    TAG_SETTINGS_NSF_WINDOW,
    TAG_SETTINGS_RENDER_BUTTON_CLOSE,
    TAG_SETTINGS_RENDER_WINDOW,
)
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_core.constants.enums import ChannelName


class MissingControlError(AssertionError):
    """Raised when a scenario presses a control the screen draws nowhere."""


class ExportProgress:
    """The window an export holds the screen with while it runs: the stages it reached, and Cancel."""

    def __init__(
        self,
        bridge: Bridge,
        hand: Hand,
    ) -> None:
        self._bridge = bridge
        self._hand = hand

    def is_shown(self) -> bool:
        """Whether the window stands on the screen."""
        return self._bridge.ask(lambda: read_item(TAG_SETTINGS_EXPORT_WINDOW)).shown

    def stages(self) -> Tuple[str, ...]:
        """The stages the window lists, in the order the run reached them."""
        return self._bridge.ask(lambda: read_shown_texts(TAG_SETTINGS_EXPORT_GROUP_STAGES))

    def cancel(self) -> None:
        """Clicks Cancel, which asks the run to stop."""
        self._hand.click(compose_tag(TAG_SETTINGS_EXPORT_BUTTON_CANCEL, SUF_BUTTON))


class NSFWindow:
    """The window setting an NSF program up: its channels, its repeat, its level of compression,
    its title and file.
    """

    def __init__(
        self,
        bridge: Bridge,
        hand: Hand,
    ) -> None:
        self._bridge = bridge
        self._hand = hand

    def is_shown(self) -> bool:
        """Whether the window stands on the screen."""
        return self._bridge.ask(lambda: read_item(TAG_SETTINGS_NSF_WINDOW)).shown

    def offers(self, channel: ChannelName) -> bool:
        """Whether ``channel``'s box answers a press, which it does for a channel the source sounds."""
        return self._bridge.ask(lambda: read_item(_channel_box(channel))).enabled

    def is_ticked(self, channel: ChannelName) -> bool:
        """Whether ``channel``'s box stands ticked."""
        return bool(self._bridge.ask(lambda: read_value(_channel_box(channel))))

    def tick(self, channel: ChannelName) -> None:
        """Clicks ``channel``'s box, which ticks it or lets it go."""
        self._hand.click(_channel_box(channel))

    def press_on(self, channel: ChannelName) -> None:
        """Clicks where ``channel``'s box stands, whether or not the box answers."""
        rect = self._bridge.ask(lambda: read_item(_channel_box(channel))).rect
        if rect is None:
            raise MissingControlError(f"The box of {channel} stands nowhere")

        self._hand.click_at(rect.center)

    def says_a_channel_is_needed(self) -> bool:
        """Whether the line asking for at least one channel stands in the window."""
        return self._bridge.ask(lambda: read_item(TAG_SETTINGS_NSF_TEXT_NO_CHANNEL)).shown

    def can_export(self) -> bool:
        """Whether Export answers a press."""
        return self._bridge.ask(lambda: read_item(_export_button())).enabled

    def press_export(self) -> None:
        """Clicks where Export stands, whether or not it answers."""
        rect = self._bridge.ask(lambda: read_item(_export_button())).rect
        if rect is None:
            raise MissingControlError("Export stands nowhere")

        self._hand.click_at(rect.center)

    def export(self) -> None:
        """Clicks Export, which writes the program to the file chosen."""
        self._hand.click(_export_button())

    def browse(self) -> None:
        """Clicks Browse..., which asks for the file the program is written to."""
        self._hand.click(compose_tag(TAG_SETTINGS_NSF_BUTTON_BROWSE, SUF_BUTTON))

    def cancel(self) -> None:
        """Clicks Cancel, which closes the window."""
        self._hand.click(compose_tag(TAG_SETTINGS_NSF_BUTTON_CANCEL, SUF_BUTTON))

    def repeat(self) -> str:
        """The way of repeating the Repeat list names."""
        return str(self._bridge.ask(lambda: read_value(TAG_SETTINGS_NSF_COMBO_REPEAT)))

    def choose_repeat(self, label: str) -> None:
        """Picks the way of repeating reading ``label`` in the Repeat list."""
        self._bridge.ask(lambda: choose(TAG_SETTINGS_NSF_COMBO_REPEAT, label, CallbackQueue.run))

    def level(self) -> str:
        """The level of compression the Level list names."""
        return str(self._bridge.ask(lambda: read_value(TAG_SETTINGS_NSF_COMBO_SCHEME)))

    def choose_level(self, label: str) -> None:
        """Picks the level of compression reading ``label`` in the Level list."""
        self._bridge.ask(lambda: choose(TAG_SETTINGS_NSF_COMBO_SCHEME, label, CallbackQueue.run))

    def loop_frame(self) -> str:
        """What the Frame field reads, in hexadecimal."""
        return str(self._bridge.ask(lambda: read_value(TAG_SETTINGS_NSF_INPUT_LOOP_FRAME)))

    def type_loop_frame(self, frame: str) -> None:
        """Types ``frame`` in hexadecimal into the Frame field, in place of what it held."""
        self._hand.replace_text(TAG_SETTINGS_NSF_INPUT_LOOP_FRAME, frame)

    def title(self) -> str:
        """What the Title field reads."""
        return str(self._bridge.ask(lambda: read_value(TAG_SETTINGS_NSF_INPUT_TITLE)))

    def type_title(self, title: str) -> None:
        """Types ``title`` into the Title field, in place of what it held."""
        self._hand.replace_text(TAG_SETTINGS_NSF_INPUT_TITLE, title)


class RenderWindow:
    """The window rendering the song to an audio file: its format, its destination, and Render and Cancel."""

    def __init__(
        self,
        bridge: Bridge,
        hand: Hand,
    ) -> None:
        self._bridge = bridge
        self._hand = hand

    def is_shown(self) -> bool:
        """Whether the window stands on the screen."""
        return self._bridge.ask(lambda: read_item(TAG_SETTINGS_RENDER_WINDOW)).shown

    def cancel(self) -> None:
        """Clicks Cancel on a window whose render has yet to start, which closes the window."""
        self._hand.click(compose_tag(TAG_SETTINGS_RENDER_BUTTON_CLOSE, SUF_BUTTON))


class Exports:
    """The ways a project, a reconstruction or an instrument leaves the application as a file.

    A project is exported from File ▸ Export, a reconstruction's channels from Reconstruction ▸ Export
    instruments. An export runs under its window, and its outcome stands in a notice: the project's names the
    format it was written in, and an instrument's names the file it wrote.
    """

    def __init__(
        self,
        bridge: Bridge,
        hand: Hand,
        menu: MenuBar,
    ) -> None:
        self._bridge = bridge
        self._menu = menu
        self.progress = ExportProgress(bridge, hand)
        self.nsf = NSFWindow(bridge, hand)
        self.render = RenderWindow(bridge, hand)
        self.project_notice = Notice(bridge, hand, TAG_GLOBAL_DIALOG_MODULE_EXPORTED)
        self.file_notice = Notice(bridge, hand, TAG_GLOBAL_DIALOG_PATH_MESSAGE)

    def export_project(self, item: MenuElements) -> None:
        """Chooses File ▸ Export ▸ ``item``."""
        self._menu.choose(MenuElements.GROUP_FILE, item)

    def render_song(self) -> None:
        """Chooses File ▸ Render song, which opens the window rendering the song."""
        self._menu.choose(MenuElements.GROUP_FILE, MenuElements.ITEM_FILE_RENDER_SONG)

    def export_reconstruction(self, item: MenuElements) -> None:
        """Chooses Reconstruction ▸ Export instruments ▸ ``item``."""
        self._menu.choose(MenuElements.GROUP_RECONSTRUCTION, item)


def _channel_box(channel: ChannelName) -> str:
    return compose_tag(TAG_SETTINGS_NSF_CHECKBOX_CHANNEL, channel.value)


def _export_button() -> str:
    return compose_tag(TAG_SETTINGS_NSF_BUTTON_EXPORT, SUF_BUTTON)
