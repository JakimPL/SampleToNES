from pathlib import Path
from typing import Final, List

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.categories.context import channel_label
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.config import LayoutConfig
from sampletones_application.paths import LANG_EN
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import SUF_BUTTON
from sampletones_application.tags.settings import (
    TAG_SETTINGS_NSF_BUTTON_BROWSE,
    TAG_SETTINGS_NSF_BUTTON_CANCEL,
    TAG_SETTINGS_NSF_BUTTON_EXPORT,
    TAG_SETTINGS_NSF_CHECKBOX_CHANNEL,
    TAG_SETTINGS_NSF_COMBO_REPEAT,
    TAG_SETTINGS_NSF_COMBO_SCHEME,
    TAG_SETTINGS_NSF_GROUP_LOOP_FRAME,
    TAG_SETTINGS_NSF_INPUT_ARTIST,
    TAG_SETTINGS_NSF_INPUT_LOOP_FRAME,
    TAG_SETTINGS_NSF_INPUT_TITLE,
    TAG_SETTINGS_NSF_PATH_DESTINATION,
    TAG_SETTINGS_NSF_TEXT_FRAME_COUNT,
    TAG_SETTINGS_NSF_TEXT_LENGTH,
    TAG_SETTINGS_NSF_TEXT_NO_CHANNEL,
    TAG_SETTINGS_NSF_TEXT_SCHEME_DESCRIPTION,
    TAG_SETTINGS_NSF_TEXT_TITLE_SIZE,
)
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.panels.dialogs.nsf import GUINSFExportWindow
from sampletones_application.utils.gui.keyboard import KeyRouter
from sampletones_application.view_model.shared.nsf.choices import NSFExportChoices
from sampletones_application.view_model.shared.nsf.offer import NSFExportOffer
from sampletones_application.view_model.shared.nsf.repeat import NSFRepeat
from sampletones_application.view_model.shared.nsf.view import NSFExportViewModel
from sampletones_core.constants.enums import ChannelName
from sampletones_player.compression.scheme import CompressionScheme
from sampletones_player.nsf.information import fit_field
from sampletones_player.specification.nsf import STRING_TEXT_SIZE
from sampletones_shared.utils.system.paths import shorten_path
from tests.suite.nsf import PROGRAM_ARTIST, PROGRAM_TITLE, project_offer, sample_offer, standing_choices
from tests.suite.shortcuts import shipped_source

LANGUAGE_MANAGER: Final[LanguageManager] = LanguageManager(LANG_EN)
DESTINATION: Final[Path] = Path("/home/user/programs/chiptune.nsf")
SONG_TICKS: Final[int] = 10800
NES_FREQUENCY: Final[int] = 60
LOOP_FRAME: Final[int] = 2
OVERLONG_TITLE: Final[str] = "Überraschungsmelodie für Konsolen"


def export_view(offer: NSFExportOffer, choices: NSFExportChoices) -> NSFExportViewModel:
    return NSFExportViewModel(
        offer=offer,
        choices=choices,
        destination=DESTINATION,
        ticks=SONG_TICKS,
        nes_frequency=NES_FREQUENCY,
    )


@pytest.fixture(name="window")
def window_fixture(dpg_context: None, layout_config: LayoutConfig) -> GUINSFExportWindow:
    return GUINSFExportWindow(
        layout=layout_config.settings,
        path_colors=layout_config.general.colors.paths,
        text_colors=layout_config.general.colors.text,
        language_manager=LANGUAGE_MANAGER,
        key_router=KeyRouter(),
        shortcut_source=shipped_source(),
        status_bar=GUIStatusBar(display_time=1.0),
    )


def draw(window: GUINSFExportWindow, view_model: NSFExportViewModel) -> None:
    """Builds the widget tree for the given state, the way ``open`` does without a live frame."""
    window.update_view(view_model)
    window.create_window()


def draw_project(window: GUINSFExportWindow) -> NSFExportViewModel:
    offer = project_offer()
    view_model = export_view(offer, standing_choices(offer))
    draw(window, view_model)
    return view_model


def channel_tag(channel: ChannelName) -> str:
    return compose_tag(TAG_SETTINGS_NSF_CHECKBOX_CHANNEL, channel.value)


def press(tag: str) -> None:
    dpg.get_item_callback(compose_tag(tag, SUF_BUTTON))()


def edit(tag: str, value: object) -> None:
    """Reports an edit the way DearPyGui does, handing the user data to a control that carries some."""
    user_data = dpg.get_item_user_data(tag)
    if user_data is None:
        dpg.get_item_callback(tag)(tag, value)
    else:
        dpg.get_item_callback(tag)(tag, value, user_data)


class TestTheProgramText:
    def test_each_field_shows_its_text(self, window: GUINSFExportWindow) -> None:
        draw_project(window)

        assert dpg.get_value(TAG_SETTINGS_NSF_INPUT_TITLE) == PROGRAM_TITLE
        assert dpg.get_value(TAG_SETTINGS_NSF_INPUT_ARTIST) == PROGRAM_ARTIST

    def test_each_field_states_the_bytes_its_text_takes(self, window: GUINSFExportWindow) -> None:
        view_model = draw_project(window)

        expected = view_model.text_size_label(PROGRAM_TITLE, LANGUAGE_MANAGER["settings.nsf.template.text_size"])
        assert dpg.get_value(TAG_SETTINGS_NSF_TEXT_TITLE_SIZE) == expected

    def test_a_typed_title_is_reported_as_the_header_holds_it(self, window: GUINSFExportWindow) -> None:
        reported: List[NSFExportChoices] = []
        window.on_choices_changed = reported.append
        draw_project(window)

        edit(TAG_SETTINGS_NSF_INPUT_TITLE, OVERLONG_TITLE * 2)

        assert reported[-1].information.title == fit_field(OVERLONG_TITLE * 2)
        assert len(reported[-1].information.title.encode()) <= STRING_TEXT_SIZE


class TestTheChannels:
    def test_a_channel_the_source_sounds_takes_a_tick(self, window: GUINSFExportWindow) -> None:
        offer = sample_offer()
        draw(window, export_view(offer, standing_choices(offer)))

        for channel in ChannelName.items():
            configuration = dpg.get_item_configuration(channel_tag(channel))
            assert configuration["enabled"] == (channel in offer.channels)
            assert dpg.get_value(channel_tag(channel)) == (channel in offer.channels)

    def test_each_channel_is_named_as_everywhere_else(self, window: GUINSFExportWindow) -> None:
        draw_project(window)

        for channel in ChannelName.items():
            label = channel_label(LANGUAGE_MANAGER, channel)
            assert dpg.get_item_configuration(channel_tag(channel))["label"] == label

    def test_unticking_a_channel_reports_it(self, window: GUINSFExportWindow) -> None:
        reported: List[NSFExportChoices] = []
        window.on_choices_changed = reported.append
        draw_project(window)

        edit(channel_tag(ChannelName.NOISE), False)

        assert ChannelName.NOISE not in reported[-1].channels

    def test_a_program_sounding_nothing_says_why_it_waits(self, window: GUINSFExportWindow) -> None:
        offer = project_offer()
        choices = standing_choices(offer).model_copy(update={"channels": frozenset()})
        draw(window, export_view(offer, choices))

        assert dpg.get_item_configuration(TAG_SETTINGS_NSF_TEXT_NO_CHANNEL)["show"]
        assert not dpg.get_item_configuration(TAG_SETTINGS_NSF_BUTTON_EXPORT)["enabled"]

    def test_a_sounding_program_says_nothing(self, window: GUINSFExportWindow) -> None:
        draw_project(window)

        assert not dpg.get_item_configuration(TAG_SETTINGS_NSF_TEXT_NO_CHANNEL)["show"]
        assert dpg.get_item_configuration(TAG_SETTINGS_NSF_BUTTON_EXPORT)["enabled"]


class TestThePlayback:
    def test_the_repeats_offered_are_the_sources(self, window: GUINSFExportWindow) -> None:
        offer = sample_offer()
        draw(window, export_view(offer, standing_choices(offer)))

        assert dpg.get_item_configuration(TAG_SETTINGS_NSF_COMBO_REPEAT)["items"] == [
            LANGUAGE_MANAGER["settings.nsf.label.repeat_once"],
            LANGUAGE_MANAGER["settings.nsf.label.repeat_from_start"],
        ]

    def test_the_frame_is_asked_for_once_the_repeat_returns_to_one(self, window: GUINSFExportWindow) -> None:
        offer = project_offer()
        choices = standing_choices(offer).with_repeat(NSFRepeat.FROM_FRAME, offer).with_loop_frame(LOOP_FRAME, offer)
        view_model = export_view(offer, choices)
        draw(window, view_model)

        assert dpg.get_item_configuration(TAG_SETTINGS_NSF_GROUP_LOOP_FRAME)["show"]
        assert dpg.get_value(TAG_SETTINGS_NSF_INPUT_LOOP_FRAME) == view_model.loop_frame_label(
            LANGUAGE_MANAGER["settings.nsf.template.frame"]
        )
        assert dpg.get_value(TAG_SETTINGS_NSF_TEXT_FRAME_COUNT) == view_model.frame_count_label(
            LANGUAGE_MANAGER["settings.nsf.template.frame_count"]
        )

    def test_a_repeat_from_the_start_leaves_the_frame_out(self, window: GUINSFExportWindow) -> None:
        draw_project(window)

        assert not dpg.get_item_configuration(TAG_SETTINGS_NSF_GROUP_LOOP_FRAME)["show"]
        assert not dpg.get_item_configuration(TAG_SETTINGS_NSF_INPUT_LOOP_FRAME)["enabled"]

    def test_the_length_is_stated(self, window: GUINSFExportWindow) -> None:
        view_model = draw_project(window)

        expected = view_model.length_label(LANGUAGE_MANAGER["settings.nsf.template.length"])
        assert dpg.get_value(TAG_SETTINGS_NSF_TEXT_LENGTH) == expected

    def test_picking_a_repeat_reports_it(self, window: GUINSFExportWindow) -> None:
        reported: List[NSFExportChoices] = []
        window.on_choices_changed = reported.append
        draw_project(window)

        edit(TAG_SETTINGS_NSF_COMBO_REPEAT, LANGUAGE_MANAGER["settings.nsf.label.repeat_from_frame"])

        assert reported[-1].repeat == NSFRepeat.FROM_FRAME

    def test_a_typed_frame_is_read_in_hexadecimal(self, window: GUINSFExportWindow) -> None:
        reported: List[NSFExportChoices] = []
        window.on_choices_changed = reported.append
        draw_project(window)

        edit(TAG_SETTINGS_NSF_INPUT_LOOP_FRAME, "0A")

        assert reported[-1].loop_frame == 10

    def test_a_field_typed_empty_reports_nothing(self, window: GUINSFExportWindow) -> None:
        reported: List[NSFExportChoices] = []
        window.on_choices_changed = reported.append
        draw_project(window)

        edit(TAG_SETTINGS_NSF_INPUT_LOOP_FRAME, "")

        assert not reported


class TestTheCompression:
    def test_the_schemes_offered_are_the_sources(self, window: GUINSFExportWindow) -> None:
        offer = sample_offer()
        draw(window, export_view(offer, standing_choices(offer)))

        assert LANGUAGE_MANAGER["settings.nsf.label.scheme_instruments"] not in (
            dpg.get_item_configuration(TAG_SETTINGS_NSF_COMBO_SCHEME)["items"]
        )

    def test_the_chosen_scheme_is_described(self, window: GUINSFExportWindow) -> None:
        offer = project_offer()
        draw(window, export_view(offer, standing_choices(offer).with_scheme(CompressionScheme.RUNS, offer)))

        assert dpg.get_value(TAG_SETTINGS_NSF_COMBO_SCHEME) == LANGUAGE_MANAGER["settings.nsf.label.scheme_runs"]
        assert (
            dpg.get_value(TAG_SETTINGS_NSF_TEXT_SCHEME_DESCRIPTION)
            == LANGUAGE_MANAGER["settings.nsf.message.scheme_runs"]
        )

    def test_picking_a_scheme_reports_it(self, window: GUINSFExportWindow) -> None:
        reported: List[NSFExportChoices] = []
        window.on_choices_changed = reported.append
        draw_project(window)

        edit(TAG_SETTINGS_NSF_COMBO_SCHEME, LANGUAGE_MANAGER["settings.nsf.label.scheme_none"])

        assert reported[-1].scheme == CompressionScheme.NONE


class TestTheActions:
    def test_the_file_is_shown(self, window: GUINSFExportWindow) -> None:
        draw_project(window)

        assert dpg.get_value(TAG_SETTINGS_NSF_PATH_DESTINATION) == shorten_path(DESTINATION)

    def test_the_browse_button_asks_for_a_file(self, window: GUINSFExportWindow) -> None:
        asked: List[None] = []
        window.on_browse = lambda: asked.append(None)
        draw_project(window)

        press(TAG_SETTINGS_NSF_BUTTON_BROWSE)

        assert asked

    def test_the_export_button_hands_the_export_over(self, window: GUINSFExportWindow) -> None:
        exported: List[None] = []
        window.on_export = lambda: exported.append(None)
        draw_project(window)

        press(TAG_SETTINGS_NSF_BUTTON_EXPORT)

        assert exported

    def test_a_program_sounding_nothing_is_kept_from_the_export(self, window: GUINSFExportWindow) -> None:
        exported: List[None] = []
        window.on_export = lambda: exported.append(None)
        offer = project_offer()
        draw(window, export_view(offer, standing_choices(offer).model_copy(update={"channels": frozenset()})))

        press(TAG_SETTINGS_NSF_BUTTON_EXPORT)

        assert not exported

    def test_the_cancel_button_closes_the_dialog(self, window: GUINSFExportWindow) -> None:
        closed: List[None] = []
        window.on_close = lambda: closed.append(None)
        draw_project(window)

        press(TAG_SETTINGS_NSF_BUTTON_CANCEL)

        assert closed
