from typing import Optional

import dearpygui.dearpygui as dpg

from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import SUF_CHANNELS, SUF_CHECKBOX
from sampletones_application.tags.main import PRE_MAIN_SOURCE_CHANNEL, TAG_MAIN_SOURCE_TEXT_SUBJECT
from sampletones_core.constants.enums import ChannelName
from tests.suite.screens.dearpygui.bridge import Bridge
from tests.suite.screens.dearpygui.hand import Hand
from tests.suite.screens.dearpygui.items import read_theme


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
        return compose_tag(PRE_MAIN_SOURCE_CHANNEL, channel, SUF_CHANNELS, SUF_CHECKBOX)

    def channel_ticked(self, channel: ChannelName) -> bool:
        return bool(self._bridge.ask(lambda: dpg.get_value(self.channel_box(channel))))

    def channel_theme(self, channel: ChannelName) -> Optional[str]:
        return self._bridge.ask(lambda: read_theme(self.channel_box(channel)))

    def tick(self, channel: ChannelName) -> None:
        self._hand.scroll_into_view(self.channel_box(channel))
        self._hand.click(self.channel_box(channel))
