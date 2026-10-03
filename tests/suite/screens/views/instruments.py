from typing import Final, Optional, Tuple

from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import SUF_BUTTON, SUF_GROUP, SUF_TABLE, SUF_TEXT
from sampletones_application.tags.graphs import SUF_GRAPH, SUF_GRAPH_RAW_DATA
from sampletones_application.tags.reconstructions import (
    SUF_RECONSTRUCTIONS_INSTRUMENTS_INSTRUMENT_SIZE,
    SUF_RECONSTRUCTIONS_INSTRUMENTS_WINDOW,
    TAG_RECONSTRUCTIONS_INSTRUMENTS_BUTTON_EXPORT_INSTRUMENT,
    TAG_RECONSTRUCTIONS_INSTRUMENTS_RADIO_AUDITION,
    TAG_RECONSTRUCTIONS_INSTRUMENTS_TABS_BAR,
)
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_core.constants.enums import ChannelName, FeatureKey
from tests.suite.screens.dearpygui.bridge import Bridge
from tests.suite.screens.dearpygui.hand import Hand
from tests.suite.screens.dearpygui.items.colors import read_theme
from tests.suite.screens.dearpygui.items.reading import read_item, read_selected_tab, read_value
from tests.suite.screens.dearpygui.items.texts import read_label
from tests.suite.screens.dearpygui.keys import IMGUI_ENTER
from tests.suite.screens.dearpygui.semantic import choose
from tests.suite.screens.views.bar_graph import BarGraph

AUDITION_GROUP: Final[str] = compose_tag(TAG_RECONSTRUCTIONS_INSTRUMENTS_RADIO_AUDITION, SUF_GROUP)


class Instruments:
    """The instruments card: a tab per channel, each with a graph and a field per envelope it governs."""

    def __init__(
        self,
        bridge: Bridge,
        hand: Hand,
    ) -> None:
        self._bridge = bridge
        self._hand = hand

    def bring_forward(self, channel: ChannelName) -> None:
        """Clicks the tab of ``channel``."""
        self._hand.click(tab(channel))

    def front(self) -> str:
        """The tag of the tab standing in front."""
        return self._bridge.ask(lambda: read_selected_tab(TAG_RECONSTRUCTIONS_INSTRUMENTS_TABS_BAR))

    def tab_label(self, channel: ChannelName) -> str:
        """What ``channel``'s tab reads, which names the open hand-written voice on the tab it is edited
        under.
        """
        return self._bridge.ask(lambda: read_label(tab(channel)))

    def tab_shown(self, channel: ChannelName) -> bool:
        """Whether ``channel``'s tab stands on the screen."""
        return self._bridge.ask(lambda: read_item(tab(channel))).shown

    def tab_theme(self, channel: ChannelName) -> Optional[str]:
        """The theme ``channel``'s tab wears, which mutes the tab of a channel that plays nothing."""
        return self._bridge.ask(lambda: read_theme(tab(channel)))

    def size(self, channel: ChannelName) -> str:
        """What ``channel``'s tab reads as the size of the instrument it exports."""
        return str(
            self._bridge.ask(
                lambda: read_value(compose_tag(tab(channel), SUF_RECONSTRUCTIONS_INSTRUMENTS_INSTRUMENT_SIZE))
            )
        )

    def rows(self, channel: ChannelName) -> Tuple[FeatureKey, ...]:
        """The envelopes ``channel``'s tab draws a row for, top to bottom."""

        def read() -> Tuple[FeatureKey, ...]:
            return tuple(feature for feature in FeatureKey if read_item(_row(channel, feature)).shown)

        return self._bridge.ask(read)

    def field(self, channel: ChannelName, feature: FeatureKey) -> str:
        """The name of the field holding the sequence of ``channel``'s ``feature`` envelope."""
        return compose_tag(TAG_RECONSTRUCTIONS_INSTRUMENTS_TABS_BAR, channel, feature, SUF_GRAPH_RAW_DATA, SUF_TEXT)

    def envelope(self, channel: ChannelName, feature: FeatureKey) -> str:
        """The sequence the field under ``channel``'s ``feature`` graph holds, as the reader would edit it."""
        return str(self._bridge.ask(lambda: read_value(self.field(channel, feature))))

    def field_theme(self, channel: ChannelName, feature: FeatureKey) -> Optional[str]:
        """The theme the field wears, which marks a sequence refused or one an export shortens."""
        return self._bridge.ask(lambda: read_theme(self.field(channel, feature)))

    def hover_field(self, channel: ChannelName, feature: FeatureKey) -> None:
        """Rests the pointer on ``channel``'s ``feature`` field, which puts what the field takes on the
        status bar.
        """
        field = self.field(channel, feature)
        self._hand.scroll_into_view(field)
        rect = self._bridge.ask(lambda: read_item(field).rect)
        if rect is None:
            raise LookupError(f"The field '{field}' stands nowhere")

        self._hand.move_to(rect.center)

    def type_envelope(self, channel: ChannelName, feature: FeatureKey, sequence: str) -> None:
        """Brings ``channel``'s tab forward, types ``sequence`` over its ``feature`` field and presses
        Enter.
        """
        self.bring_forward(channel)
        field = self.field(channel, feature)
        self._hand.scroll_into_view(field)
        self._hand.replace_text(field, sequence)
        self._hand.press_key(IMGUI_ENTER, modifiers=[])

    def graph(self, channel: ChannelName, feature: FeatureKey) -> BarGraph:
        """The graph drawn for ``channel``'s ``feature`` envelope."""
        return BarGraph(
            self._bridge, self._hand, compose_tag(TAG_RECONSTRUCTIONS_INSTRUMENTS_TABS_BAR, channel, feature, SUF_GRAPH)
        )

    def offers_pitch_stepper(self, channel: ChannelName) -> bool:
        """Whether ``channel``'s tab offers the stepper setting the pitch its arpeggio is read against."""
        window = compose_tag(tab(channel), SUF_RECONSTRUCTIONS_INSTRUMENTS_WINDOW)
        return self._bridge.ask(lambda: read_item(compose_tag(window, SUF_TABLE))).shown

    def offers_audition(self) -> bool:
        """Whether the Audition switch stands, which it does while a hand-written instrument is open."""
        return self._bridge.ask(lambda: read_item(AUDITION_GROUP)).shown

    def audition(self) -> str:
        """The generator the Audition switch names."""
        return str(self._bridge.ask(lambda: read_value(TAG_RECONSTRUCTIONS_INSTRUMENTS_RADIO_AUDITION)))

    def choose_audition(self, label: str) -> None:
        """Picks the generator reading ``label`` in the Audition list."""
        self._bridge.ask(lambda: choose(TAG_RECONSTRUCTIONS_INSTRUMENTS_RADIO_AUDITION, label, CallbackQueue.run))

    def can_export(self, channel: ChannelName) -> bool:
        """Whether ``channel``'s Export instrument button answers."""
        return self._bridge.ask(lambda: read_item(export_button(channel))).enabled

    def export(self, channel: ChannelName) -> None:
        """Clicks ``channel``'s Export instrument button."""
        self._hand.scroll_into_view(export_button(channel))
        self._hand.click(export_button(channel))


def tab(channel: ChannelName) -> str:
    """The name of the tab of ``channel``."""
    return compose_tag(TAG_RECONSTRUCTIONS_INSTRUMENTS_TABS_BAR, channel)


def export_button(channel: ChannelName) -> str:
    """The name of the Export instrument button of ``channel``."""
    return compose_tag(TAG_RECONSTRUCTIONS_INSTRUMENTS_BUTTON_EXPORT_INSTRUMENT, tab(channel), SUF_BUTTON)


def _row(channel: ChannelName, feature: FeatureKey) -> str:
    return compose_tag(TAG_RECONSTRUCTIONS_INSTRUMENTS_TABS_BAR, channel, feature, SUF_GROUP)
