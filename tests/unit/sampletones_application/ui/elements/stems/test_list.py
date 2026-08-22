from pathlib import Path
from typing import Final, FrozenSet, Iterator, List, Tuple

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.categories.manager import LanguageManager
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
from sampletones_application.tags.general import (
    SUF_BUTTON,
    SUF_CHANNELS,
    SUF_CHECKBOX,
    SUF_LEVEL,
    SUF_ROW,
    SUF_STRIP,
    SUF_TEXT,
    TAG_GLOBAL_THEME_STEMS_ROW,
    TAG_GLOBAL_THEME_STEMS_ROW_INERT,
)
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.elements.stems.list import GUIStemsList
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.ui.themes.setup import setup_themes
from sampletones_application.utils.palette.catalog import PaletteCatalog
from sampletones_application.utils.palette.source import PaletteSource
from sampletones_application.view_model.shared.stems import (
    StemRowViewModel,
    StemsListViewModel,
)
from sampletones_core.constants.enums import ChannelName

ROOT_TAG = "test_root"
PREFIX = "test.stems"
CHANNELS: Tuple[ChannelName, ...] = (ChannelName.PULSE1, ChannelName.TRIANGLE)
DRAG_PAYLOAD_SLOT: Final[int] = 3


@pytest.fixture
def layout_config() -> LayoutConfig:
    source = PaletteSource(PaletteCatalog.load(PALETTES_DIRECTORY).default)
    return load_layout_config(LAYOUT_DIRECTORY, BEHAVIOR_DIRECTORY, source)


@pytest.fixture
def dpg_context(layout_config: LayoutConfig) -> Iterator[None]:
    """Stands up the context, fonts and themes the list binds while it draws."""
    dpg.create_context()
    FontRegistry.setup(layout_config.fonts)
    FontRegistry.register_fonts(layout_config.fonts.scale)
    setup_themes(THEME_DIRECTORY, PaletteSource(PaletteCatalog.load(PALETTES_DIRECTORY).default))
    try:
        yield
    finally:
        ThemeRegistry.clear()
        dpg.destroy_context()


def build(
    layout_config: LayoutConfig,
    *,
    draggable: bool = True,
    removable: bool = True,
) -> GUIStemsList:
    stems_list = GUIStemsList(
        prefix=PREFIX,
        layout=layout_config.general.stems,
        language_manager=LanguageManager(LANG_EN),
        status_bar=GUIStatusBar(),
        draggable=draggable,
        removable=removable,
    )
    with dpg.window(tag=ROOT_TAG):
        stems_list.create(ROOT_TAG)

    return stems_list


def row(
    name: str,
    *,
    channels: FrozenSet[ChannelName] = frozenset(CHANNELS),
    level: int = 0,
    position: int = 0,
    level_size: int = 1,
    level_count: int = 1,
) -> StemRowViewModel:
    path = Path(f"/audio/{name}.wav")
    return StemRowViewModel(
        key=str(path),
        path=path,
        channels=channels,
        level=level,
        position=position,
        level_size=level_size,
        level_count=level_count,
    )


def view(*rows: StemRowViewModel, live: bool = True) -> StemsListViewModel:
    return StemsListViewModel(rows=rows, channels_in_play=CHANNELS, live=live)


def row_tag(entry: StemRowViewModel, suffix: str) -> str:
    return compose_tag(PREFIX, SUF_ROW, entry.key, suffix)


def channel_tag(entry: StemRowViewModel, channel_name: ChannelName) -> str:
    return compose_tag(PREFIX, SUF_ROW, entry.key, SUF_CHANNELS, compose_tag(channel_name, SUF_CHECKBOX))


class TestRows:
    def test_a_row_names_its_recording_and_offers_every_channel_in_play(self, dpg_context: None, layout_config) -> None:
        stems_list = build(layout_config)
        bass = row("bass")

        stems_list.update_view(view(bass))

        assert dpg.get_item_label(row_tag(bass, SUF_TEXT)) == "bass"
        for channel_name in CHANNELS:
            assert dpg.get_value(channel_tag(bass, channel_name))

    def test_a_channel_the_row_lacks_reads_unticked(self, dpg_context: None, layout_config) -> None:
        stems_list = build(layout_config)
        bass = row("bass", channels=frozenset({ChannelName.PULSE1}))

        stems_list.update_view(view(bass))

        assert dpg.get_value(channel_tag(bass, ChannelName.PULSE1))
        assert not dpg.get_value(channel_tag(bass, ChannelName.TRIANGLE))

    def test_a_row_holding_no_channel_greys_out_and_still_answers(
        self,
        dpg_context: None,
        layout_config,
    ) -> None:
        stems_list = build(layout_config)
        bass = row("bass", channels=frozenset())

        stems_list.update_view(view(bass))

        name_tag = row_tag(bass, SUF_TEXT)
        assert dpg.get_item_alias(dpg.get_item_theme(name_tag)) == TAG_GLOBAL_THEME_STEMS_ROW_INERT
        assert dpg.is_item_enabled(name_tag)

    def test_a_row_taking_part_reads_in_full(self, dpg_context: None, layout_config) -> None:
        stems_list = build(layout_config)
        bass = row("bass")

        stems_list.update_view(view(bass))

        assert dpg.get_item_alias(dpg.get_item_theme(row_tag(bass, SUF_TEXT))) == TAG_GLOBAL_THEME_STEMS_ROW

    def test_rows_follow_a_changed_list(self, dpg_context: None, layout_config) -> None:
        stems_list = build(layout_config)
        bass, lead = row("bass"), row("lead")
        stems_list.update_view(view(bass, lead, live=True))

        stems_list.update_view(view(lead))

        assert not dpg.does_item_exist(row_tag(bass, SUF_TEXT))
        assert dpg.does_item_exist(row_tag(lead, SUF_TEXT))

    def test_the_list_reports_the_row_a_gesture_named(self, dpg_context: None, layout_config) -> None:
        stems_list = build(layout_config)
        bass = row("bass")

        stems_list.update_view(view(bass))

        assert stems_list.row(bass.key) == bass
        assert stems_list.row("nothing") is None


class TestLevels:
    def test_each_level_carries_its_own_band(self, dpg_context: None, layout_config) -> None:
        stems_list = build(layout_config)
        rows = (
            row("bass", level=0, level_count=2),
            row("drums", level=1, level_count=2),
        )

        stems_list.update_view(view(*rows))

        assert dpg.get_value(compose_tag(PREFIX, SUF_LEVEL, "0", SUF_TEXT)) == "LEVEL 1"
        assert dpg.get_value(compose_tag(PREFIX, SUF_LEVEL, "1", SUF_TEXT)) == "LEVEL 2"

    def test_a_draggable_list_opens_a_strip_above_each_level_and_below_the_last(
        self, dpg_context: None, layout_config
    ) -> None:
        stems_list = build(layout_config)
        rows = (
            row("bass", level=0, level_count=2),
            row("drums", level=1, level_count=2),
        )

        stems_list.update_view(view(*rows))

        for position in range(3):
            assert dpg.does_item_exist(compose_tag(PREFIX, SUF_LEVEL, str(position), SUF_STRIP))


class TestAffordances:
    def test_a_draggable_list_makes_the_row_itself_the_thing_you_drag(
        self,
        dpg_context: None,
        layout_config,
    ) -> None:
        stems_list = build(layout_config, draggable=True)
        bass = row("bass")

        stems_list.update_view(view(bass))

        assert dpg.get_item_children(row_tag(bass, SUF_TEXT), DRAG_PAYLOAD_SLOT)

    def test_a_list_without_dragging_carries_no_payload_and_no_strip(
        self,
        dpg_context: None,
        layout_config,
    ) -> None:
        stems_list = build(layout_config, draggable=False)
        bass = row("bass")

        stems_list.update_view(view(bass))

        assert not dpg.get_item_children(row_tag(bass, SUF_TEXT), DRAG_PAYLOAD_SLOT)
        assert not dpg.does_item_exist(compose_tag(PREFIX, SUF_LEVEL, "0", SUF_STRIP))

    def test_a_removable_list_gives_each_row_a_button(self, dpg_context: None, layout_config) -> None:
        stems_list = build(layout_config, removable=True)
        bass = row("bass")

        stems_list.update_view(view(bass))

        assert dpg.does_item_exist(row_tag(bass, SUF_BUTTON))

    def test_a_list_without_removal_gives_no_button(self, dpg_context: None, layout_config) -> None:
        stems_list = build(layout_config, removable=False)
        bass = row("bass")

        stems_list.update_view(view(bass))

        assert not dpg.does_item_exist(row_tag(bass, SUF_BUTTON))


class TestGestures:
    def test_unticking_a_channel_reports_the_row_and_what_it_keeps(self, dpg_context: None, layout_config) -> None:
        reported: List[Tuple[str, FrozenSet[ChannelName]]] = []
        stems_list = build(layout_config)
        stems_list.on_channels_changed = lambda key, channels: reported.append((key, channels))
        bass = row("bass")
        stems_list.update_view(view(bass))

        tag = channel_tag(bass, ChannelName.TRIANGLE)
        dpg.set_value(tag, False)
        dpg.get_item_callback(tag)(tag, False, dpg.get_item_user_data(tag))

        assert reported == [(bass.key, frozenset({ChannelName.PULSE1}))]

    def test_the_remove_button_reports_its_row(self, dpg_context: None, layout_config) -> None:
        removed: List[str] = []
        stems_list = build(layout_config)
        stems_list.on_remove_requested = removed.append
        bass = row("bass")
        stems_list.update_view(view(bass))

        tag = row_tag(bass, SUF_BUTTON)
        dpg.get_item_callback(tag)(tag, None, dpg.get_item_user_data(tag))

        assert removed == [bass.key]


class TestBusyState:
    def test_a_list_that_is_not_live_disables_every_control_it_drew(self, dpg_context: None, layout_config) -> None:
        stems_list = build(layout_config)
        bass = row("bass")

        stems_list.update_view(view(bass, live=False))

        assert not dpg.is_item_enabled(row_tag(bass, SUF_TEXT))
        assert not dpg.is_item_enabled(row_tag(bass, SUF_BUTTON))
        for channel_name in CHANNELS:
            assert not dpg.is_item_enabled(channel_tag(bass, channel_name))

    def test_a_live_list_answers_again(self, dpg_context: None, layout_config) -> None:
        stems_list = build(layout_config)
        bass = row("bass")
        stems_list.update_view(view(bass, live=False))

        stems_list.update_view(view(bass, live=True))

        assert dpg.is_item_enabled(row_tag(bass, SUF_TEXT))
        assert dpg.is_item_enabled(row_tag(bass, SUF_BUTTON))
