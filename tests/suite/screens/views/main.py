from typing import Optional

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.output import OutputKind
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
    SUF_BUTTON,
    SUF_COLLAPSE_BODY,
    SUF_COLLAPSE_RAIL,
    SUF_COLLAPSE_STRIP,
    SUF_TOOLTIP,
    TAG_GLOBAL_THEME_STEP_BUTTON_LIT,
)
from sampletones_application.tags.main import (
    PRE_MAIN_SOURCE_STEP,
    TAG_MAIN_ADVANCED_BUTTON_SELECT_LIBRARY_DIRECTORY,
    TAG_MAIN_ADVANCED_PANEL,
    TAG_MAIN_ADVANCED_PATH_LIBRARY_DIRECTORY_DISPLAY,
    TAG_MAIN_CONVERTER_RADIO_MODE,
)
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_application.view_model.main.source import CHANNEL_CAP_STEPS
from tests.suite.screens.dearpygui.bridge import Bridge
from tests.suite.screens.dearpygui.hand import Hand
from tests.suite.screens.dearpygui.items import read_item, read_texts, read_theme, read_value
from tests.suite.screens.dearpygui.semantic import choose
from tests.suite.screens.views.converter import Converter
from tests.suite.screens.views.source import SourceSettings

OUTPUT_LABEL_KEYS = {
    OutputKind.PER_RECORDING: "main.converter.label.mode_each",
    OutputKind.MIXED: "main.converter.label.mode_mixed",
}


class Card:
    """A card of the interface that folds into its header bar at a click on the bar."""

    def __init__(
        self,
        bridge: Bridge,
        hand: Hand,
        tag: str,
    ) -> None:
        self._bridge = bridge
        self._hand = hand
        self.tag = tag

    def is_shown(self) -> bool:
        return self._bridge.ask(lambda: read_item(self.tag)).shown

    def is_collapsed(self) -> bool:
        """Whether the card stands folded into its bar, its body put away."""
        return not self._bridge.ask(lambda: read_item(compose_tag(self.tag, SUF_COLLAPSE_BODY))).shown

    def toggle(self) -> None:
        """Clicks the card's header bar, which folds an open card and opens a folded one."""
        strip = compose_tag(self.tag, SUF_COLLAPSE_STRIP)
        self._hand.scroll_into_view(strip)
        self._hand.click(strip)

    def folds_sideways(self) -> bool:
        """Whether the card folds into a rail at its side, rather than into its bar."""
        return self._bridge.ask(lambda: read_item(self.rail)).exists

    @property
    def rail(self) -> str:
        """The rail a sideways card folds into, which a click unfolds."""
        return compose_tag(self.tag, SUF_COLLAPSE_RAIL)

    @property
    def strip(self) -> str:
        """The header bar a click folds the card on."""
        return compose_tag(self.tag, SUF_COLLAPSE_STRIP)

    def unfold_from_the_rail(self) -> None:
        """Clicks the rail a sideways card stands folded into, which unfolds it."""
        self._hand.click(self.rail)


class Main:
    """The Main tab: its cards, the converter's settings and the folders the advanced settings name."""

    def __init__(
        self,
        bridge: Bridge,
        hand: Hand,
        language: LanguageManager,
    ) -> None:
        self._bridge = bridge
        self._hand = hand
        self._language = language
        self.advanced = Card(bridge, hand, TAG_MAIN_ADVANCED_PANEL)
        self.converter = Converter(bridge, hand)
        self.source = SourceSettings(bridge, hand)

    def card(self, tag: str) -> Card:
        return Card(self._bridge, self._hand, tag)

    def output(self) -> OutputKind:
        """What the converter's output switch stands at."""
        label = self._bridge.ask(lambda: read_value(TAG_MAIN_CONVERTER_RADIO_MODE))
        for output, key in OUTPUT_LABEL_KEYS.items():
            if self._language[key] == label:
                return output

        raise LookupError(f"The output switch reads '{label}', which names no output")

    def choose_output(self, output: OutputKind) -> None:
        """Picks ``output`` on the converter's output switch."""
        label = self._language[OUTPUT_LABEL_KEYS[output]]
        self._bridge.ask(lambda: choose(TAG_MAIN_CONVERTER_RADIO_MODE, label, CallbackQueue.run))

    def choose_channels_at_once(self, count: int) -> None:
        """Clicks the step naming ``count`` channels at once."""
        self._hand.scroll_into_view(_step_tag(count))
        self._hand.click(_step_tag(count))

    def lit_channels_at_once(self) -> Optional[int]:
        """The step of Channels at once that stands lit, if one does."""

        def read() -> Optional[int]:
            for step in CHANNEL_CAP_STEPS:
                if read_theme(_step_tag(step)) == TAG_GLOBAL_THEME_STEP_BUTTON_LIT:
                    return step

            return None

        return self._bridge.ask(read)

    def choose_library_directory(self) -> None:
        """Clicks the button that asks for the library folder."""
        button = compose_tag(TAG_MAIN_ADVANCED_BUTTON_SELECT_LIBRARY_DIRECTORY, SUF_BUTTON)
        self._hand.scroll_into_view(button)
        self._hand.click(button)

    def library_directory(self) -> str:
        """The whole path of the library folder, as the hover over its shortened path shows it."""
        tooltip = compose_tag(TAG_MAIN_ADVANCED_PATH_LIBRARY_DIRECTORY_DISPLAY, SUF_TOOLTIP)
        return " ".join(self._bridge.ask(lambda: read_texts(tooltip)))


def _step_tag(step: int) -> str:
    return compose_tag(PRE_MAIN_SOURCE_STEP, str(step), SUF_BUTTON)
