from typing import FrozenSet, Iterator, List, Optional, Tuple

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.sources import SettingsField, SourceKind
from sampletones_application.layout.config import LayoutConfig
from sampletones_application.layout.loader import load_layout_config
from sampletones_application.paths import (
    BEHAVIOR_DIRECTORY,
    LANG_EN,
    LAYOUT_DIRECTORY,
    PALETTES_DIRECTORY,
    THEME_DIRECTORY,
)
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import SUF_HEADING, SUF_TEXT
from sampletones_application.tags.main import (
    PRE_MAIN_SOURCE_SLOT,
    TAG_MAIN_SOURCE_GROUP_GRID,
    TAG_MAIN_SOURCE_SLIDER_DRIVE,
    TAG_MAIN_SOURCE_TABLE_GRID,
    TAG_MAIN_SOURCE_TEXT_INSPECTING,
    TAG_MAIN_SOURCE_TEXT_UNPICKED,
)
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.panels.main.source.panel import GUISourceSettingsPanel
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.ui.themes.setup import setup_themes
from sampletones_application.utils.palette.catalog import PaletteCatalog
from sampletones_application.utils.palette.source import PaletteSource
from sampletones_application.view_model.main.source import (
    InspectedSourceViewModel,
    SettingsSlotViewModel,
    SourceSettingsPanelViewModel,
)
from sampletones_core.constants.enums import TONE_CHANNELS, ChannelName

ROOT_TAG = "test_root"
DRIVE = 1.5
HELD_RECORDINGS = 1939


@pytest.fixture
def layout_config() -> LayoutConfig:
    source = PaletteSource(PaletteCatalog.load(PALETTES_DIRECTORY).default)
    return load_layout_config(LAYOUT_DIRECTORY, BEHAVIOR_DIRECTORY, source)


@pytest.fixture
def dpg_context(layout_config: LayoutConfig) -> Iterator[None]:
    """Stands up the context, fonts, themes and header geometry the card draws under."""
    dpg.create_context()
    FontRegistry.setup(layout_config.fonts)
    FontRegistry.register_fonts(layout_config.fonts.scale)
    setup_themes(THEME_DIRECTORY, PaletteSource(PaletteCatalog.load(PALETTES_DIRECTORY).default))
    GUIPanel.configure_section_header(
        layout_config.glyphs,
        layout_config.general.section_header,
        layout_config.general.collapse,
    )
    try:
        yield
    finally:
        ThemeRegistry.clear()
        dpg.destroy_context()


def slot(
    field: SettingsField,
    *,
    offered: FrozenSet[ChannelName],
    held: FrozenSet[ChannelName] = frozenset(),
    partial: FrozenSet[ChannelName] = frozenset(),
) -> SettingsSlotViewModel:
    return SettingsSlotViewModel(
        field=field,
        offered_channels=offered,
        held_channels=held,
        partial_channels=partial,
    )


def view(
    *slots: SettingsSlotViewModel,
    inspected: Optional[InspectedSourceViewModel] = None,
    live: bool = True,
) -> SourceSettingsPanelViewModel:
    return SourceSettingsPanelViewModel(
        slots=slots,
        inspected=inspected,
        drive=DRIVE,
        live=live,
    )


def recording(name: str) -> InspectedSourceViewModel:
    return InspectedSourceViewModel(name=name, kind=SourceKind.RECORDING, holds=1)


def folder(name: str, holds: int) -> InspectedSourceViewModel:
    return InspectedSourceViewModel(name=name, kind=SourceKind.FOLDER, holds=holds)


def channels_slot(*, held: FrozenSet[ChannelName] = frozenset()) -> SettingsSlotViewModel:
    return slot(SettingsField.CHANNELS, offered=frozenset(ChannelName.items()), held=held)


def build(
    layout_config: LayoutConfig,
    initial: SourceSettingsPanelViewModel,
) -> Tuple[GUISourceSettingsPanel, List[Tuple[SettingsField, ChannelName]]]:
    """The card as the application builds it, over the choices it reports."""
    panel = GUISourceSettingsPanel(
        initial,
        layout=layout_config.tabs.main.source,
        inputs=layout_config.general.inputs,
        stems_layout=layout_config.general.stems,
        language_manager=LanguageManager(LANG_EN),
        status_bar=GUIStatusBar(),
    )
    reported: List[Tuple[SettingsField, ChannelName]] = []
    panel.on_slot_toggled = lambda field, channel: reported.append((field, channel))
    with dpg.window(tag=ROOT_TAG):
        panel.create_panel(ROOT_TAG)

    return panel, reported


def box_tag(field: SettingsField, channel_name: ChannelName) -> str:
    return compose_tag(PRE_MAIN_SOURCE_SLOT, field.value, channel_name.value)


def shows(tag: str) -> bool:
    return bool(dpg.get_item_configuration(tag)["show"])


class TestDrive:
    """Drive answers for the run as a whole, so it stands whatever the reader is looking at."""

    def test_it_stands_with_nothing_picked(self, dpg_context: None, layout_config: LayoutConfig) -> None:
        build(layout_config, view())

        assert dpg.get_value(TAG_MAIN_SOURCE_SLIDER_DRIVE) == pytest.approx(DRIVE)

    def test_it_stands_above_the_row_the_card_edits(self, dpg_context: None, layout_config: LayoutConfig) -> None:
        build(layout_config, view())
        body = dpg.get_item_children(dpg.get_item_parent(TAG_MAIN_SOURCE_TEXT_INSPECTING), 1)
        drive = dpg.get_item_parent(TAG_MAIN_SOURCE_SLIDER_DRIVE)

        assert body.index(drive) < body.index(dpg.get_alias_id(TAG_MAIN_SOURCE_TEXT_INSPECTING))


class TestNothingPicked:
    """With no row picked the card says which gesture gives it one."""

    def test_the_hint_stands(self, dpg_context: None, layout_config: LayoutConfig) -> None:
        build(layout_config, view())

        assert shows(TAG_MAIN_SOURCE_TEXT_UNPICKED)

    def test_the_grid_stands_away(self, dpg_context: None, layout_config: LayoutConfig) -> None:
        build(layout_config, view())

        assert not shows(TAG_MAIN_SOURCE_GROUP_GRID)

    def test_the_row_is_named_by_nothing(self, dpg_context: None, layout_config: LayoutConfig) -> None:
        build(layout_config, view())

        assert not shows(TAG_MAIN_SOURCE_TEXT_INSPECTING)


class TestAPickedRow:
    """A picked row is named above the grid its choices stand in."""

    def test_a_recording_reads_its_own_name(self, dpg_context: None, layout_config: LayoutConfig) -> None:
        panel, _reported = build(layout_config, view())

        panel.update_view(view(channels_slot(), inspected=recording("bass")))

        assert dpg.get_value(TAG_MAIN_SOURCE_TEXT_INSPECTING) == "bass"

    def test_a_folder_reads_how_many_it_stands_for(self, dpg_context: None, layout_config: LayoutConfig) -> None:
        panel, _reported = build(layout_config, view())

        panel.update_view(view(channels_slot(), inspected=folder("VEH2 Loops", HELD_RECORDINGS)))

        named = dpg.get_value(TAG_MAIN_SOURCE_TEXT_INSPECTING)
        assert named.startswith("VEH2 Loops")
        assert str(HELD_RECORDINGS) in named

    def test_the_grid_comes_with_it(self, dpg_context: None, layout_config: LayoutConfig) -> None:
        panel, _reported = build(layout_config, view())

        panel.update_view(view(channels_slot(), inspected=recording("bass")))

        assert shows(TAG_MAIN_SOURCE_GROUP_GRID)
        assert not shows(TAG_MAIN_SOURCE_TEXT_UNPICKED)


class TestTheGrid:
    """The channels are named once above the row, and each cell holds the boxes it offers."""

    def test_the_grid_rules_the_names_off_from_the_boxes(
        self,
        dpg_context: None,
        layout_config: LayoutConfig,
    ) -> None:
        """The heading draws no rule of its own, so the grid below it is what divides the two."""
        build(layout_config, view())

        assert dpg.get_item_configuration(TAG_MAIN_SOURCE_TABLE_GRID)["borders_outerH"] is True

    def test_every_channel_is_named(self, dpg_context: None, layout_config: LayoutConfig) -> None:
        build(layout_config, view())

        for channel_name in ChannelName.items():
            assert dpg.does_item_exist(compose_tag(TAG_MAIN_SOURCE_GROUP_GRID, SUF_HEADING, channel_name, SUF_TEXT))

    def test_a_channel_the_row_takes_reads_ticked(self, dpg_context: None, layout_config: LayoutConfig) -> None:
        panel, _reported = build(layout_config, view())

        panel.update_view(
            view(
                channels_slot(held=frozenset({ChannelName.PULSE1})),
                inspected=recording("bass"),
            )
        )

        assert dpg.get_value(box_tag(SettingsField.CHANNELS, ChannelName.PULSE1)) is True
        assert dpg.get_value(box_tag(SettingsField.CHANNELS, ChannelName.PULSE2)) is False

    def test_a_channel_the_folder_half_holds_reads_clear(self, dpg_context: None, layout_config: LayoutConfig) -> None:
        """A tick would state an answer the folder has yet to give, so a divided reading is clear."""
        panel, _reported = build(layout_config, view())

        panel.update_view(
            view(
                slot(
                    SettingsField.CHANNELS,
                    offered=frozenset(ChannelName.items()),
                    partial=frozenset({ChannelName.PULSE1}),
                ),
                inspected=folder("takes", 2),
            )
        )

        assert dpg.get_value(box_tag(SettingsField.CHANNELS, ChannelName.PULSE1)) is False

    def test_a_bend_stands_only_where_its_channel_reads_one(
        self,
        dpg_context: None,
        layout_config: LayoutConfig,
    ) -> None:
        panel, _reported = build(layout_config, view())

        panel.update_view(
            view(
                channels_slot(held=frozenset(TONE_CHANNELS)),
                slot(SettingsField.BENDS, offered=frozenset(TONE_CHANNELS)),
                inspected=recording("bass"),
            )
        )

        assert shows(box_tag(SettingsField.BENDS, ChannelName.TRIANGLE))
        assert not dpg.does_item_exist(box_tag(SettingsField.BENDS, ChannelName.NOISE))

    def test_a_running_conversion_holds_the_boxes(self, dpg_context: None, layout_config: LayoutConfig) -> None:
        panel, _reported = build(layout_config, view())

        panel.update_view(view(channels_slot(), inspected=recording("bass"), live=False))

        assert dpg.get_item_configuration(box_tag(SettingsField.CHANNELS, ChannelName.PULSE1))["enabled"] is False


class TestTheChoicesTheCardReports:
    """The card settles nothing itself: it names the choice a reader made and hands it on."""

    @pytest.mark.parametrize("channel", list(ChannelName.items()))
    def test_a_box_names_the_choice_and_the_channel_it_stands_on(
        self,
        channel: ChannelName,
        dpg_context: None,
        layout_config: LayoutConfig,
    ) -> None:
        _panel, reported = build(layout_config, view(channels_slot(), inspected=recording("bass")))

        callback = dpg.get_item_callback(box_tag(SettingsField.CHANNELS, channel))
        callback(None, True, dpg.get_item_user_data(box_tag(SettingsField.CHANNELS, channel)))

        assert reported == [(SettingsField.CHANNELS, channel)]


class TestBoxTags:
    def test_every_choice_and_channel_carries_a_tag_of_its_own(
        self,
        dpg_context: None,
        layout_config: LayoutConfig,
    ) -> None:
        build(layout_config, view())
        tags = tuple(
            box_tag(field, channel)
            for channel in ChannelName.items()
            for field in SettingsField
            if dpg.does_item_exist(box_tag(field, channel))
        )

        assert len(set(tags)) == len(tags)
        assert tags
