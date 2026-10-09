from typing import Optional

import dearpygui.dearpygui as dpg

from automation.dearpygui.bridge import Bridge
from automation.dearpygui.hand import Hand
from automation.dearpygui.items.colors import read_theme
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import SUF_CHANNELS, SUF_CHECKBOX
from sampletones_application.tags.main import (
    PRE_MAIN_SOURCE_CHANNEL,
    TAG_MAIN_SOURCE_TEXT_SUBJECT,
)
from sampletones_core.constants.enums import ChannelName


class SourceSettings:
    """The Source settings card: what the picked row converts with, channel by channel."""

    def __init__(
        self,
        bridge: Bridge,
        hand: Hand,
    ) -> None:
        self._bridge = bridge
        self._hand = hand

    def subject(self) -> str:
        """What the card names as the row it speaks for."""
        return str(self._bridge.ask(lambda: dpg.get_value(TAG_MAIN_SOURCE_TEXT_SUBJECT)))

    def channel_box(self, channel: ChannelName) -> str:
        """The tag of the checkbox that lets the row convert with ``channel``."""
        return compose_tag(PRE_MAIN_SOURCE_CHANNEL, channel, SUF_CHANNELS, SUF_CHECKBOX)

    def channel_ticked(self, channel: ChannelName) -> bool:
        """Whether the checkbox of ``channel`` stands ticked."""
        return bool(self._bridge.ask(lambda: dpg.get_value(self.channel_box(channel))))

    def channel_theme(self, channel: ChannelName) -> Optional[str]:
        """The theme the checkbox of ``channel`` wears, or ``None`` while it wears none."""
        return self._bridge.ask(lambda: read_theme(self.channel_box(channel)))

    def tick(self, channel: ChannelName) -> None:
        """Clicks the checkbox of ``channel``, scrolling it into view first."""
        self._hand.scroll_into_view(self.channel_box(channel))
        self._hand.click(self.channel_box(channel))
