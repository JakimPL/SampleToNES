from functools import partial
from typing import Dict, Final

import dearpygui.dearpygui as dpg

from automation.dearpygui.items.reading import read_item
from automation.screen import Screen
from automation.steps.main import home_path
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import SUF_TEXT, TAG_GLOBAL_THEME_STEMS_GROUP_ROW
from sampletones_application.tags.main import PRE_MAIN_CONVERTER_STEMS
from sampletones_application.ui.themes.channels import CHANNEL_THEME_TAGS
from sampletones_core.constants.enums import ChannelName
from tests.screens.main.list.constants import FORTY
from tests.screens.main.list.steps import gather
from tests.suite.screens.seeds.constants import KICK

SAME_LINE_PIXELS: Final[float] = 1.0
HEADING: Final[str] = "heading"

CHANNEL_NAMES: Final[Dict[ChannelName, str]] = {
    ChannelName.PULSE1: "global.context.label.pulse_1",
    ChannelName.PULSE2: "global.context.label.pulse_2",
    ChannelName.TRIANGLE: "global.context.label.triangle",
    ChannelName.NOISE: "global.context.label.noise",
}


class TestTheListsLook:
    """The channel names above the list wear their channel's color; a folder row carries the band and has a
    recording's height.

    A recording and a folder are gathered. The scenario reads the heading texts and themes, the band
    theme of each row, the row heights and the line shared by a recording's name and its boxes.
    """

    def test_names_bands_and_lines(self, screen: Screen) -> None:
        """Names, bands, heights and lines match what the list should look like."""
        listing = screen.main.converter.list
        folder = home_path(FORTY)

        def gather_a_recording_and_a_folder(screen: Screen) -> None:
            gather(screen, home_path(KICK), folder)

        def the_channel_names_wear_their_colours(screen: Screen) -> None:
            for channel, key in CHANNEL_NAMES.items():
                name = compose_tag(PRE_MAIN_CONVERTER_STEMS, HEADING, channel, SUF_TEXT)

                assert screen.bridge.ask(partial(dpg.get_value, name)) == screen.words(key)
                assert screen.theme_of(name) == CHANNEL_THEME_TAGS[channel]

        def the_folder_alone_carries_the_band(screen: Screen) -> None:
            assert listing.band_theme(folder) == TAG_GLOBAL_THEME_STEMS_GROUP_ROW
            assert listing.band_theme(home_path(KICK)) != TAG_GLOBAL_THEME_STEMS_GROUP_ROW

        def rows_share_a_height_and_names_share_a_line_with_their_boxes(screen: Screen) -> None:
            folder_box = screen.bridge.ask(lambda: read_item(listing.row(folder)).rect)
            recording_box = screen.bridge.ask(lambda: read_item(listing.row(home_path(KICK))).rect)
            check_box = screen.bridge.ask(
                lambda: read_item(listing.channel_box(home_path(KICK), ChannelName.PULSE1)).rect
            )
            assert folder_box is not None and recording_box is not None and check_box is not None

            assert folder_box.height == recording_box.height
            assert (
                abs((recording_box.y + recording_box.height / 2) - (check_box.y + check_box.height / 2))
                <= SAME_LINE_PIXELS
            )

        screen.scenario(
            gather_a_recording_and_a_folder,
            the_channel_names_wear_their_colours,
            the_folder_alone_carries_the_band,
            rows_share_a_height_and_names_share_a_line_with_their_boxes,
        ).run()
