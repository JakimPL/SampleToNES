from pathlib import Path
from typing import Final, List, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import SUF_BUTTON, SUF_CHECKBOX, SUF_DIALOG_INFO, SUF_TOOLTIP
from sampletones_application.tags.main import (
    PRE_MAIN_CONVERTER_CANDIDATE,
    PRE_MAIN_CONVERTER_STEMS,
    TAG_MAIN_CONVERTER_BUTTON_ACTION,
    TAG_MAIN_CONVERTER_BUTTON_ADD_STEMS,
    TAG_MAIN_CONVERTER_BUTTON_CANCEL_STEMS,
    TAG_MAIN_CONVERTER_BUTTON_STOP_SCAN,
    TAG_MAIN_CONVERTER_DIALOG_CANCEL,
    TAG_MAIN_CONVERTER_DIALOG_DISCARD_STEMS,
    TAG_MAIN_CONVERTER_DIALOG_LOAD,
    TAG_MAIN_CONVERTER_DIALOG_OVERWRITE_TARGET,
    TAG_MAIN_CONVERTER_GROUP,
    TAG_MAIN_CONVERTER_PANEL,
    TAG_MAIN_CONVERTER_PROGRESS,
    TAG_MAIN_CONVERTER_TEXT_OUTPUT_PATH,
    TAG_MAIN_CONVERTER_TEXT_SCAN_FOLDER,
    TAG_MAIN_CONVERTER_TEXT_STATUS,
    TAG_MAIN_CONVERTER_TEXT_STEM_SELECTION_LIMIT,
    TAG_MAIN_CONVERTER_TEXT_STEMS_HINT,
    TAG_MAIN_CONVERTER_WINDOW_SCAN,
    TAG_MAIN_CONVERTER_WINDOW_STEM_SELECTION,
    TAG_MAIN_EXPLORER_DIALOG_NOTHING_BELOW,
)
from sampletones_application.ui.elements.stems.tags import StemsTags
from sampletones_core.constants.enums import ChannelName
from tests.suite.screens.dearpygui.bridge import Bridge
from tests.suite.screens.dearpygui.hand import Hand
from tests.suite.screens.dearpygui.items.colors import read_theme
from tests.suite.screens.dearpygui.items.reading import find_item, read_item
from tests.suite.screens.dearpygui.items.texts import read_label, read_texts
from tests.suite.screens.dearpygui.items.types import Item
from tests.suite.screens.views.notices import Notice
from tests.suite.screens.views.prompts import Prompt

ROW_TEXT: Final[str] = "text"
ROW_GROUP: Final[str] = "group"
ROW_TWISTY: Final[str] = "twisty"
ROW_REMOVE: Final[str] = "button"
ROW_MARK: Final[str] = ".row."
FIRST_LEVEL: Final[int] = 0
LEVEL_STRIP: Final[str] = "strip"


class ConverterList:
    """The recordings and folders gathered into the Converter card, one row each.

    A row is named by the path it was gathered from, so a scenario addresses the row of the file
    it seeded. A folder's row carries a marker that opens it onto its recordings.
    """

    def __init__(
        self,
        bridge: Bridge,
        hand: Hand,
    ) -> None:
        self._bridge = bridge
        self._hand = hand
        self.tags = StemsTags(prefix=PRE_MAIN_CONVERTER_STEMS)

    def row(self, path: Path) -> str:
        """The name of the row gathered from ``path``, which a click picks."""
        return self.tags.row(str(path), ROW_TEXT)

    def has_row(self, path: Path) -> bool:
        """Whether a row gathered from ``path`` is drawn."""
        return bool(self._bridge.ask(lambda: dpg.does_item_exist(self.row(path))))

    def label(self, path: Path) -> str:
        """The words the row of ``path`` reads."""
        return self._bridge.ask(lambda: read_label(self.row(path)))

    def is_picked(self, path: Path) -> bool:
        """Whether the row of ``path`` stands picked."""
        return bool(self._bridge.ask(lambda: dpg.get_value(self.row(path))))

    def row_theme(self, path: Path) -> Optional[str]:
        """The theme the row of ``path`` wears, or None when it wears none."""
        return self._bridge.ask(lambda: read_theme(self.row(path)))

    def band_theme(self, path: Path) -> Optional[str]:
        """The theme the band behind the row of ``path`` wears, or None when it wears none."""
        return self._bridge.ask(lambda: read_theme(self.tags.row(str(path), ROW_GROUP)))

    def rows(self) -> List[str]:
        """The names of every row drawn, top to bottom, as the tags they stand under."""

        def read() -> List[str]:
            found: List[str] = []
            find_item(self.tags.well, lambda item: _collect_row(item, found))
            return found

        return self._bridge.ask(read)

    def row_count(self) -> int:
        """How many rows are drawn, folders included."""
        return len(self.rows())

    def channel_box(self, path: Path, channel: ChannelName) -> str:
        """The name of the box ticking ``channel`` on the row of ``path``."""
        return self.tags.channel(str(path), channel)

    def channel_ticked(self, path: Path, channel: ChannelName) -> bool:
        """Whether ``channel``'s box on the row of ``path`` stands ticked."""
        return bool(self._bridge.ask(lambda: dpg.get_value(self.channel_box(path, channel))))

    def channel_theme(self, path: Path, channel: ChannelName) -> Optional[str]:
        """The theme ``channel``'s box on the row of ``path`` wears, or None when it wears none."""
        return self._bridge.ask(lambda: read_theme(self.channel_box(path, channel)))

    def twisty(self, path: Path) -> str:
        """The name of the marker that opens the folder gathered from ``path``."""
        return self.tags.row(str(path), ROW_TWISTY)

    def is_open(self, path: Path) -> bool:
        """Whether the folder gathered from ``path`` stands open onto its recordings."""
        return bool(self._bridge.ask(lambda: dpg.does_item_exist(self.tags.region(str(path)))))

    def remove_button(self, path: Path) -> str:
        """The name of the button removing the row of ``path``."""
        return self.tags.row(str(path), ROW_REMOVE)

    def has_levels(self) -> bool:
        """Whether the list stands in level bands, which a mix of several recordings draws."""
        return bool(self._bridge.ask(lambda: dpg.does_item_exist(self.tags.level(FIRST_LEVEL, LEVEL_STRIP))))

    def hint_shown(self) -> bool:
        """Whether the hint asking for recordings stands on the card."""
        return self._bridge.ask(lambda: read_item(TAG_MAIN_CONVERTER_TEXT_STEMS_HINT)).shown

    def list_shown(self) -> bool:
        """Whether the list of rows stands on the card."""
        return self._bridge.ask(lambda: read_item(self.tags.well)).shown

    def pick(self, path: Path) -> None:
        """Brings the row into view and clicks its name."""
        self._hand.scroll_into_view(self.row(path))
        self._hand.click(self.row(path))

    def tick(self, path: Path, channel: ChannelName) -> None:
        """Brings the row into view and clicks its box for ``channel``."""
        self._hand.scroll_into_view(self.channel_box(path, channel))
        self._hand.click(self.channel_box(path, channel))

    def toggle_folder(self, path: Path) -> None:
        """Clicks the marker beside a folder's name."""
        self._hand.scroll_into_view(self.twisty(path))
        self._hand.click(self.twisty(path))

    def remove(self, path: Path) -> None:
        """Clicks the row's remove button."""
        self._hand.scroll_into_view(self.remove_button(path))
        self._hand.click(self.remove_button(path))


class MixQuestion:
    """The question picking which recordings a mix takes, once more are gathered than a mix holds."""

    def __init__(
        self,
        bridge: Bridge,
        hand: Hand,
    ) -> None:
        self._bridge = bridge
        self._hand = hand
        self.tags = StemsTags(prefix=PRE_MAIN_CONVERTER_CANDIDATE)

    def is_shown(self) -> bool:
        """Whether the question stands on the screen."""
        return self._bridge.ask(lambda: read_item(TAG_MAIN_CONVERTER_WINDOW_STEM_SELECTION)).shown

    def box(self, path: Path) -> str:
        """The name of the box ticking the recording at ``path``."""
        return self.tags.row(str(path), SUF_CHECKBOX)

    def name(self, path: Path) -> str:
        """The name of the line showing the recording at ``path``."""
        return self.tags.row(str(path), ROW_TEXT)

    def is_ticked(self, path: Path) -> bool:
        """Whether the box of the recording at ``path`` stands ticked."""
        return bool(self._bridge.ask(lambda: dpg.get_value(self.box(path))))

    def is_live(self, path: Path) -> bool:
        """Whether the box answers a click, which a box beyond a full pick stops doing."""
        return self._bridge.ask(lambda: read_item(self.box(path))).enabled

    def is_highlighted(self, path: Path) -> bool:
        """Whether the line of the recording at ``path`` stands highlighted."""
        return bool(self._bridge.ask(lambda: dpg.get_value(self.name(path))))

    def count_line(self) -> str:
        """What the line counting the recordings picked reads."""
        return str(self._bridge.ask(lambda: dpg.get_value(TAG_MAIN_CONVERTER_TEXT_STEM_SELECTION_LIMIT)))

    def can_add(self) -> bool:
        """Whether Add answers a click."""
        return self._bridge.ask(lambda: read_item(_add_button())).enabled

    def tick(self, path: Path) -> None:
        """Brings the box of the recording at ``path`` into view and clicks it."""
        self._hand.scroll_into_view(self.box(path))
        self._hand.click(self.box(path))

    def add(self) -> None:
        """Clicks Add, which takes the recordings ticked."""
        self._hand.click(_add_button())

    def cancel(self) -> None:
        """Clicks Cancel, which closes the question and takes no recording."""
        self._hand.click(compose_tag(TAG_MAIN_CONVERTER_BUTTON_CANCEL_STEMS, SUF_BUTTON))


class Converter:
    """The Converter card: the list, the button naming the run, and the run's progress and questions.

    A scenario reaches the list, the mix question, the prompts and the notices through the attributes
    of the card.
    """

    def __init__(
        self,
        bridge: Bridge,
        hand: Hand,
    ) -> None:
        self._bridge = bridge
        self._hand = hand
        self.list = ConverterList(bridge, hand)
        self.mix_question = MixQuestion(bridge, hand)
        self.cancel_prompt = Prompt(bridge, hand, TAG_MAIN_CONVERTER_DIALOG_CANCEL)
        self.end_prompt = Prompt(bridge, hand, TAG_MAIN_CONVERTER_DIALOG_LOAD)
        self.overwrite_prompt = Prompt(bridge, hand, TAG_MAIN_CONVERTER_DIALOG_OVERWRITE_TARGET)
        self.replace_prompt = Prompt(bridge, hand, TAG_MAIN_CONVERTER_DIALOG_DISCARD_STEMS)
        self.notice = Notice(bridge, hand, compose_tag(TAG_MAIN_CONVERTER_PANEL, SUF_DIALOG_INFO))
        self.nothing_below_notice = Notice(
            bridge,
            hand,
            compose_tag(TAG_MAIN_EXPLORER_DIALOG_NOTHING_BELOW, SUF_DIALOG_INFO),
        )

    def action(self) -> str:
        """What the button under the list reads: the run it starts, or Cancel while one runs."""
        return self._bridge.ask(lambda: read_label(_action_button()))

    def press_action(self) -> None:
        """Brings the button under the list into view and clicks it."""
        self._hand.scroll_into_view(_action_button())
        self._hand.click(_action_button())

    def run_shown(self) -> bool:
        """Whether the card shows a run under way: its status line and its progress."""
        return self._bridge.ask(lambda: read_item(TAG_MAIN_CONVERTER_GROUP)).shown

    def status(self) -> str:
        """What the status line of the run reads."""
        return str(self._bridge.ask(lambda: dpg.get_value(TAG_MAIN_CONVERTER_TEXT_STATUS)))

    def progress(self) -> float:
        """How far the run has come, as a fraction."""
        return float(self._bridge.ask(lambda: dpg.get_value(TAG_MAIN_CONVERTER_PROGRESS)))

    def destination(self) -> str:
        """The whole path of the folder the run writes into, as the hover over its shortened path shows it."""
        tooltip = compose_tag(TAG_MAIN_CONVERTER_TEXT_OUTPUT_PATH, SUF_TOOLTIP)
        return " ".join(self._bridge.ask(lambda: read_texts(tooltip)))

    def scan_shown(self) -> bool:
        """Whether the window reading a folder stands on the screen."""
        return self._bridge.ask(lambda: read_item(TAG_MAIN_CONVERTER_WINDOW_SCAN)).shown

    def scan_words(self) -> str:
        """What the window reading a folder says it is reading."""
        return str(self._bridge.ask(lambda: dpg.get_value(TAG_MAIN_CONVERTER_TEXT_SCAN_FOLDER)))

    def stop_scan(self) -> None:
        """Clicks Stop on the window reading a folder."""
        self._hand.click(compose_tag(TAG_MAIN_CONVERTER_BUTTON_STOP_SCAN, SUF_BUTTON))


def _add_button() -> str:
    return compose_tag(TAG_MAIN_CONVERTER_BUTTON_ADD_STEMS, SUF_BUTTON)


def _action_button() -> str:
    return compose_tag(TAG_MAIN_CONVERTER_BUTTON_ACTION, SUF_BUTTON)


def _collect_row(item: Item, found: List[str]) -> bool:
    alias = str(dpg.get_item_alias(item))
    if ROW_MARK in alias and alias.startswith(PRE_MAIN_CONVERTER_STEMS) and alias.endswith(f".{ROW_TEXT}"):
        found.append(alias)

    return False
