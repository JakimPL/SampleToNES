from pathlib import Path
from typing import Iterator, List, Optional, Tuple

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.output import OutputKind
from sampletones_application.constants.sources import SourceKind
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
from sampletones_application.tags.general import SUF_BUTTON
from sampletones_application.tags.main import (
    TAG_MAIN_CONVERTER_BUTTON_ACTION,
    TAG_MAIN_CONVERTER_GROUP_CONTROLS,
    TAG_MAIN_CONVERTER_GROUP_CONVERT,
    TAG_MAIN_CONVERTER_GROUP_INPUT,
    TAG_MAIN_CONVERTER_GROUP_ORDER,
    TAG_MAIN_CONVERTER_GROUP_SUMMARY,
    TAG_MAIN_CONVERTER_RADIO_MODE,
    TAG_MAIN_CONVERTER_TEXT_STEMS_HINT,
    TAG_MAIN_CONVERTER_WINDOW_STEMS,
)
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.panels.main.converter.panel import GUIConverterPanel
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.ui.themes.setup import setup_themes
from sampletones_application.utils.gui.keyboard import ActivePredicate, KeyEvent, KeyRouter
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.utils.palette.catalog import PaletteCatalog
from sampletones_application.utils.palette.source import PaletteSource
from sampletones_application.view_model.main.converter import (
    ConversionPhase,
    ConverterViewModel,
)
from sampletones_application.view_model.shared.stems import StemRowViewModel
from sampletones_core.constants.algorithm import DEFAULT_STEMS_HIERARCHY_MODE
from sampletones_core.constants.enums import ChannelName
from tests.suite.shortcuts import shipped_source

ROOT_TAG = "test_root"
LANGUAGE_MANAGER = LanguageManager(LANG_EN)
ACTION_LABEL = "Convert 2 recordings"
STATUS_TEXT = "No tasks in progress."
RECORDING = Path("/audio/kick.wav")


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


def row(name: str) -> StemRowViewModel:
    path = Path(f"/audio/{name}.wav")
    return StemRowViewModel(
        key=str(path),
        kind=SourceKind.RECORDING,
        path=path,
        held=(),
        channels=frozenset({ChannelName.PULSE1}),
        partial_channels=frozenset(),
        bends=frozenset(),
        offered_channels=frozenset({ChannelName.PULSE1}),
        available=True,
        level=0,
        position=0,
        level_size=1,
        level_count=1,
    )


def view(
    *rows: StemRowViewModel,
    output: OutputKind = OutputKind.PER_RECORDING,
    phase: ConversionPhase = ConversionPhase.IDLE,
    input_path: Optional[Path] = None,
    output_path: Optional[Path] = None,
    selected_key: Optional[str] = None,
) -> ConverterViewModel:
    return ConverterViewModel(
        phase=phase,
        status_text=STATUS_TEXT,
        action_label=ACTION_LABEL,
        progress=0.0,
        input_path=input_path,
        output_path=output_path,
        is_file=True,
        other_operation_active=False,
        output=output,
        stem_sources=rows,
        channel_cap=len(ChannelName),
        max_channel_cap=len(ChannelName),
        hierarchy_mode=DEFAULT_STEMS_HIERARCHY_MODE,
        max_sources=8,
        selected_key=selected_key,
    )


def build(
    layout_config: LayoutConfig,
    *,
    key_router: Optional[KeyRouter] = None,
    tab_active: ActivePredicate = lambda: True,
) -> Tuple[GUIConverterPanel, List[OutputKind]]:
    """The card as the application builds it, over the output switch it reports."""
    panel = GUIConverterPanel(
        layout=layout_config.tabs.main.converter,
        stems_layout=layout_config.general.stems,
        inputs=layout_config.general.inputs,
        path_colors=layout_config.general.colors.paths,
        language_manager=LANGUAGE_MANAGER,
        status_bar=GUIStatusBar(),
        key_router=key_router if key_router is not None else KeyRouter(),
        shortcut_source=shipped_source(),
        tab_active=tab_active,
    )
    reported: List[OutputKind] = []
    panel.on_output_changed = reported.append
    with dpg.window(tag=ROOT_TAG):
        panel.create_panel(ROOT_TAG)

    panel.update_view(view())
    return panel, reported


def shows(tag: str) -> bool:
    return bool(dpg.get_item_configuration(tag)["show"])


class TestTheOutputSwitch:
    """The card opens on what the run writes, which the button below it repeats."""

    def test_it_offers_both_kinds_of_run(self, dpg_context: None, layout_config: LayoutConfig) -> None:
        build(layout_config)
        offered = dpg.get_item_configuration(TAG_MAIN_CONVERTER_RADIO_MODE)["items"]

        assert offered == [
            LANGUAGE_MANAGER["main.converter.label.mode_each"],
            LANGUAGE_MANAGER["main.converter.label.mode_mixed"],
        ]

    def test_it_stands_above_the_button(self, dpg_context: None, layout_config: LayoutConfig) -> None:
        build(layout_config)
        body = dpg.get_item_children(dpg.get_item_parent(TAG_MAIN_CONVERTER_GROUP_CONVERT), 1)
        switch = dpg.get_item_parent(TAG_MAIN_CONVERTER_RADIO_MODE)

        assert body.index(switch) < body.index(dpg.get_alias_id(TAG_MAIN_CONVERTER_GROUP_CONVERT))

    def test_it_reads_what_the_view_names(self, dpg_context: None, layout_config: LayoutConfig) -> None:
        panel, _reported = build(layout_config)

        panel.update_view(view(row("kick"), row("snare"), output=OutputKind.MIXED))

        assert dpg.get_value(TAG_MAIN_CONVERTER_RADIO_MODE) == LANGUAGE_MANAGER["main.converter.label.mode_mixed"]

    def test_a_reader_turning_it_reports_the_kind(self, dpg_context: None, layout_config: LayoutConfig) -> None:
        _panel, reported = build(layout_config)

        callback = dpg.get_item_callback(TAG_MAIN_CONVERTER_RADIO_MODE)
        callback(TAG_MAIN_CONVERTER_RADIO_MODE, LANGUAGE_MANAGER["main.converter.label.mode_mixed"])

        assert reported == [OutputKind.MIXED]


def action_button() -> str:
    """The button widget the action group holds, which is where its label is drawn."""
    return compose_tag(TAG_MAIN_CONVERTER_BUTTON_ACTION, SUF_BUTTON)


class TestTheActionButton:
    """The button says what the run writes, which the logic composes and the card renders."""

    def test_it_reads_the_label_the_view_carries(self, dpg_context: None, layout_config: LayoutConfig) -> None:
        panel, _reported = build(layout_config)

        panel.update_view(view(row("kick"), row("snare")))

        assert dpg.get_item_label(action_button()) == ACTION_LABEL

    def test_nothing_listed_leaves_it_waiting(self, dpg_context: None, layout_config: LayoutConfig) -> None:
        build(layout_config)

        assert dpg.get_item_configuration(action_button())["enabled"] is False


class TestTheRunControls:
    """The choices answer for what the list holds, so they arrive with it."""

    def test_they_stand_away_until_something_is_listed(self, dpg_context: None, layout_config: LayoutConfig) -> None:
        build(layout_config)

        assert not shows(TAG_MAIN_CONVERTER_GROUP_CONTROLS)

    def test_they_arrive_with_the_first_recording(self, dpg_context: None, layout_config: LayoutConfig) -> None:
        panel, _reported = build(layout_config)

        panel.update_view(view(row("kick")))

        assert shows(TAG_MAIN_CONVERTER_GROUP_CONTROLS)

    def test_the_order_arrives_with_the_second_recording_of_a_mix(
        self,
        dpg_context: None,
        layout_config: LayoutConfig,
    ) -> None:
        panel, _reported = build(layout_config)

        panel.update_view(view(row("kick"), output=OutputKind.MIXED))
        assert not shows(TAG_MAIN_CONVERTER_GROUP_ORDER)

        panel.update_view(view(row("kick"), row("snare"), output=OutputKind.MIXED))
        assert shows(TAG_MAIN_CONVERTER_GROUP_ORDER)

    def test_a_run_writing_one_apiece_has_no_order_to_take(
        self,
        dpg_context: None,
        layout_config: LayoutConfig,
    ) -> None:
        panel, _reported = build(layout_config)

        panel.update_view(view(row("kick"), row("snare")))

        assert not shows(TAG_MAIN_CONVERTER_GROUP_ORDER)

    def test_they_stand_below_the_list(self, dpg_context: None, layout_config: LayoutConfig) -> None:
        build(layout_config)
        body = dpg.get_item_children(dpg.get_item_parent(TAG_MAIN_CONVERTER_WINDOW_STEMS), 1)

        assert body.index(dpg.get_alias_id(TAG_MAIN_CONVERTER_WINDOW_STEMS)) < body.index(
            dpg.get_alias_id(TAG_MAIN_CONVERTER_GROUP_CONTROLS)
        )


class TestTheList:
    """The gathered recordings are what a run converts either way, so the list always stands."""

    def test_it_stands_whichever_run_the_switch_names(self, dpg_context: None, layout_config: LayoutConfig) -> None:
        panel, _reported = build(layout_config)
        assert shows(TAG_MAIN_CONVERTER_WINDOW_STEMS)

        panel.update_view(view(row("kick"), output=OutputKind.MIXED))

        assert shows(TAG_MAIN_CONVERTER_WINDOW_STEMS)

    def test_an_empty_list_says_how_to_fill_it(self, dpg_context: None, layout_config: LayoutConfig) -> None:
        build(layout_config)

        assert shows(TAG_MAIN_CONVERTER_TEXT_STEMS_HINT)
        assert dpg.get_value(TAG_MAIN_CONVERTER_TEXT_STEMS_HINT) == (
            LANGUAGE_MANAGER["main.converter.message.stems_empty_hint"]
        )

    def test_the_hint_leaves_with_the_first_recording(self, dpg_context: None, layout_config: LayoutConfig) -> None:
        panel, _reported = build(layout_config)

        panel.update_view(view(row("kick")))

        assert not shows(TAG_MAIN_CONVERTER_TEXT_STEMS_HINT)

    def test_an_empty_list_stands_away_so_the_hint_has_the_room(
        self,
        dpg_context: None,
        layout_config: LayoutConfig,
    ) -> None:
        """A list holding nothing draws a heading and its rules over empty room, so it stands away."""
        panel, _reported = build(layout_config)

        panel.update_view(view())

        assert not shows(panel.stems_list.tag)

    def test_the_list_comes_back_with_the_first_recording(
        self,
        dpg_context: None,
        layout_config: LayoutConfig,
    ) -> None:
        panel, _reported = build(layout_config)

        panel.update_view(view(row("kick")))

        assert shows(panel.stems_list.tag)


class TestTheKeysTheListClaims:
    """A row picked out puts the list on the keyboard, and everything else is left to travel on."""

    @staticmethod
    def _press(router: KeyRouter, shortcut_id: ShortcutId) -> bool:
        """Offer the press the shipped scheme gives ``shortcut_id`` to the scopes, as the router does."""
        combination = shipped_source().shortcut(shortcut_id).combination
        assert combination is not None
        return router.route(KeyEvent(key=combination.key, modifiers=combination.modifiers))

    def test_a_press_rests_while_no_row_is_picked_out(
        self,
        dpg_context: None,
        layout_config: LayoutConfig,
    ) -> None:
        router = KeyRouter()
        panel, _reported = build(layout_config, key_router=router)
        removed: List[Path] = []
        panel.on_source_removed = removed.append
        panel.update_view(view(row("kick")))

        assert self._press(router, ShortcutId.SOURCES_REMOVE_SOURCE) is False
        assert removed == []

    def test_a_press_rests_while_another_tab_is_in_front(
        self,
        dpg_context: None,
        layout_config: LayoutConfig,
    ) -> None:
        router = KeyRouter()
        panel, _reported = build(layout_config, key_router=router, tab_active=lambda: False)
        removed: List[Path] = []
        panel.on_source_removed = removed.append
        kick = row("kick")
        panel.update_view(view(kick, selected_key=kick.key))

        assert self._press(router, ShortcutId.SOURCES_REMOVE_SOURCE) is False
        assert removed == []

    def test_it_removes_the_recording_picked_out(self, dpg_context: None, layout_config: LayoutConfig) -> None:
        router = KeyRouter()
        panel, _reported = build(layout_config, key_router=router)
        removed: List[Path] = []
        panel.on_source_removed = removed.append
        kick = row("kick")
        panel.update_view(view(kick, selected_key=kick.key))

        assert self._press(router, ShortcutId.SOURCES_REMOVE_SOURCE) is True
        assert removed == [kick.path]

    def test_it_lets_the_row_picked_out_go(self, dpg_context: None, layout_config: LayoutConfig) -> None:
        router = KeyRouter()
        panel, _reported = build(layout_config, key_router=router)
        cleared: List[bool] = []
        panel.on_selection_cleared = lambda: cleared.append(True)
        kick = row("kick")
        panel.update_view(view(kick, selected_key=kick.key))

        assert self._press(router, ShortcutId.SOURCES_CLEAR_SELECTION) is True
        assert cleared == [True]

    def test_a_press_it_has_no_action_for_travels_on(self, dpg_context: None, layout_config: LayoutConfig) -> None:
        """The list yields whatever its category leaves unnamed, so the shortcuts still hear it."""
        router = KeyRouter()
        panel, _reported = build(layout_config, key_router=router)
        kick = row("kick")
        panel.update_view(view(kick, selected_key=kick.key))

        assert self._press(router, ShortcutId.SAVE_PROJECT) is False


class TestTheDestination:
    """Where a run writes is on screen whatever the card is doing; what it reads is not."""

    def test_it_stands_with_nothing_listed(self, dpg_context: None, layout_config: LayoutConfig) -> None:
        build(layout_config)

        assert shows(TAG_MAIN_CONVERTER_GROUP_SUMMARY)

    def test_the_input_line_waits_for_a_run(self, dpg_context: None, layout_config: LayoutConfig) -> None:
        panel, _reported = build(layout_config)

        panel.update_view(view(row("kick"), input_path=RECORDING))

        assert not shows(TAG_MAIN_CONVERTER_GROUP_INPUT)

    def test_the_input_line_names_the_recording_a_run_is_reading(
        self,
        dpg_context: None,
        layout_config: LayoutConfig,
    ) -> None:
        panel, _reported = build(layout_config)

        panel.update_view(
            view(
                row("kick"),
                phase=ConversionPhase.RUNNING,
                input_path=RECORDING,
            )
        )

        assert shows(TAG_MAIN_CONVERTER_GROUP_INPUT)
        assert panel.input_path_text.path == RECORDING
