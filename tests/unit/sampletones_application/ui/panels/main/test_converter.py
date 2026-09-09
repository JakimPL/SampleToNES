from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.categories.elements.main import ConverterStemMoveElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
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
from sampletones_application.ui.panels.main.converter import menus as menus_module
from sampletones_application.ui.panels.main.converter.panel import GUIConverterPanel
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.ui.themes.setup import setup_themes
from sampletones_application.utils.gui.keyboard import ActivePredicate, KeyEvent, KeyRouter, focus
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.utils.gui.shortcuts.source import ShortcutSource
from sampletones_application.utils.palette.catalog import PaletteCatalog
from sampletones_application.utils.palette.source import PaletteSource
from sampletones_application.view_model.main.converter import (
    ConversionPhase,
    ConverterViewModel,
)
from sampletones_application.view_model.shared.stems import StemRowViewModel
from sampletones_core.constants.algorithm import DEFAULT_STEMS_HIERARCHY_MODE
from sampletones_core.constants.enums import ChannelName
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.gestures import CLICKED, click_row_name
from tests.suite.shortcuts import rebound_source, shipped_source

ROOT_TAG = "test_root"
LANGUAGE_MANAGER = LanguageManager(LANG_EN)
ACTION_LABEL = "Convert 2 recordings"
STATUS_TEXT = "No tasks in progress."
RECORDING = Path("/audio/kick.wav")
REBOUND_REMOVAL = "Ctrl+Shift+K"
SEPARATOR = "separator"


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


def row(
    name: str,
    *,
    level: int = 0,
    position: int = 0,
    level_size: int = 1,
    level_count: int = 1,
) -> StemRowViewModel:
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
        level=level,
        position=position,
        level_size=level_size,
        level_count=level_count,
    )


def folder(name: str, *, holds: int) -> StemRowViewModel:
    """A row standing for everything gathered below one folder."""
    root = Path(f"/audio/{name}")
    return StemRowViewModel(
        key=str(root),
        kind=SourceKind.FOLDER,
        path=root,
        held=tuple(row(f"{name}/take_{index}") for index in range(holds)),
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
    shortcut_source: Optional[ShortcutSource] = None,
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
        shortcut_source=shipped_source() if shortcut_source is None else shortcut_source,
        tab_active=tab_active,
    )
    reported: List[OutputKind] = []
    panel.on_output_changed = reported.append
    with dpg.window(tag=ROOT_TAG):
        panel.create_panel(ROOT_TAG)

    panel.update_view(view())
    return panel, reported


@pytest.fixture
def registered(monkeypatch: pytest.MonkeyPatch) -> List[Dict[str, Any]]:
    """The items a menu registers, in the order a reader meets them, the rules between them included."""
    items: List[Dict[str, Any]] = []
    monkeypatch.setattr(menus_module.dpg, "add_menu_item", lambda **kwargs: items.append(kwargs) or 0)
    monkeypatch.setattr(
        menus_module.dpg,
        "add_separator",
        lambda **_kwargs: items.append({"label": SEPARATOR}) or 0,
    )
    return items


def right_click(panel: GUIConverterPanel, entry: StemRowViewModel) -> None:
    """Land a right-click on the row's name, which is what puts that row's menu up."""
    click_row_name(panel.stems_list.tags, entry.key, kind=CLICKED, button=dpg.mvMouseButton_Right)


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

    def test_a_press_rests_while_a_field_holds_the_keys(
        self,
        dpg_context: None,
        layout_config: LayoutConfig,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A reader typing a path keeps the plain keys, so Del edits the field rather than the list."""
        monkeypatch.setattr(focus, "is_field_focused", lambda: True)
        router = KeyRouter()
        panel, _reported = build(layout_config, key_router=router)
        removed: List[Path] = []
        panel.on_source_removed = removed.append
        kick = row("kick")
        panel.update_view(view(kick, selected_key=kick.key))

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

    def test_a_press_rests_while_the_list_stands_inert(
        self,
        dpg_context: None,
        layout_config: LayoutConfig,
    ) -> None:
        """A run holds the list still, so the key answers to the rule the row's own button reads."""
        router = KeyRouter()
        panel, _reported = build(layout_config, key_router=router)
        removed: List[Path] = []
        panel.on_source_removed = removed.append
        kick = row("kick")
        panel.update_view(view(kick, selected_key=kick.key, phase=ConversionPhase.RUNNING))

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

    def test_it_removes_the_folder_picked_out_and_everything_it_holds(
        self,
        dpg_context: None,
        layout_config: LayoutConfig,
    ) -> None:
        """A folder is taken out as a folder, so the recordings below it leave with it."""
        router = KeyRouter()
        panel, _reported = build(layout_config, key_router=router)
        removed: List[Path] = []
        folders: List[Path] = []
        panel.on_source_removed = removed.append
        panel.on_folder_removed = folders.append
        sources = folder("sources", holds=3)
        panel.update_view(view(sources, selected_key=sources.key))

        assert self._press(router, ShortcutId.SOURCES_REMOVE_SOURCE) is True
        assert folders == [sources.path]
        assert removed == []

    def test_a_recording_picked_out_leaves_on_its_own(
        self,
        dpg_context: None,
        layout_config: LayoutConfig,
    ) -> None:
        """A recording standing beside a folder is taken out as a recording."""
        router = KeyRouter()
        panel, _reported = build(layout_config, key_router=router)
        removed: List[Path] = []
        folders: List[Path] = []
        panel.on_source_removed = removed.append
        panel.on_folder_removed = folders.append
        kick = row("kick")
        panel.update_view(view(folder("sources", holds=2), kick, selected_key=kick.key))

        assert self._press(router, ShortcutId.SOURCES_REMOVE_SOURCE) is True
        assert removed == [kick.path]
        assert folders == []

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


class TestTheMenuARightClickPutsUp:
    """A right-click on a row raises the menu the card draws for it, over the row it landed on."""

    def test_a_right_click_raises_the_row_s_menu(
        self,
        dpg_context: None,
        layout_config: LayoutConfig,
        registered: List[Dict[str, Any]],
    ) -> None:
        """The list reports the gesture and the card answers it, which is what puts a menu up."""
        panel, _reported = build(layout_config)
        kick = row("kick")
        panel.update_view(view(kick, row("snare")))

        click_row_name(panel.stems_list.tags, kick.key, kind=CLICKED, button=dpg.mvMouseButton_Right)

        assert LANGUAGE_MANAGER["main.converter.label.context_remove_stem"] in [item["label"] for item in registered]

    def test_a_rule_divides_sounding_a_recording_from_moving_it(
        self,
        dpg_context: None,
        layout_config: LayoutConfig,
        registered: List[Dict[str, Any]],
    ) -> None:
        """Play sounds the recording where it stands; everything under the rule moves it or takes
        it off the list, so the two readings of the menu are kept apart."""
        panel, _reported = build(layout_config)
        kick = row("kick")
        panel.update_view(view(kick, row("snare")))

        right_click(panel, kick)

        labels = [item["label"] for item in registered]
        assert labels[labels.index(LANGUAGE_MANAGER["global.context.label.play"]) + 1] == SEPARATOR

    def test_the_item_a_folder_offers_opens_it_on_the_list(
        self,
        dpg_context: None,
        layout_config: LayoutConfig,
        registered: List[Dict[str, Any]],
    ) -> None:
        """The item does what the marker beside the folder's name does, so a reader reaching for
        the menu meets the same folder open."""
        panel, _reported = build(layout_config)
        sources = folder("sources", holds=3)
        panel.update_view(view(sources))

        right_click(panel, sources)
        opening = next(
            item for item in registered if item["label"] == LANGUAGE_MANAGER["main.converter.label.context_open_folder"]
        )
        opening["callback"]()

        assert panel.stems_list.stands_open(sources.key)

    def test_a_right_click_picks_the_row_it_stands_over(
        self,
        dpg_context: None,
        layout_config: LayoutConfig,
        registered: List[Dict[str, Any]],
    ) -> None:
        """The menu prints the key that removes a row, so both name the row the menu stands over."""
        panel, _reported = build(layout_config)
        selected: List[Tuple[Path, SourceKind]] = []
        panel.on_row_selected = lambda path, kind: selected.append((path, kind))
        kick, snare = row("kick"), row("snare")
        panel.update_view(view(kick, snare, selected_key=kick.key))

        click_row_name(panel.stems_list.tags, snare.key, kind=CLICKED, button=dpg.mvMouseButton_Right)

        assert selected == [(snare.path, SourceKind.RECORDING)]

    def test_a_folder_offers_what_reaches_everything_below_it(
        self,
        dpg_context: None,
        layout_config: LayoutConfig,
        registered: List[Dict[str, Any]],
    ) -> None:
        panel, _reported = build(layout_config)
        sources = folder("sources", holds=3)
        panel.update_view(view(sources))

        click_row_name(panel.stems_list.tags, sources.key, kind=CLICKED, button=dpg.mvMouseButton_Right)

        labels = [item["label"] for item in registered]
        assert LANGUAGE_MANAGER["main.converter.label.context_open_folder"] in labels
        assert LANGUAGE_MANAGER["main.converter.label.context_remove_folder"] in labels
        assert LANGUAGE_MANAGER["main.converter.label.context_remove_stem"] not in labels

    def test_an_open_folder_offers_to_close_again(
        self,
        dpg_context: None,
        layout_config: LayoutConfig,
        registered: List[Dict[str, Any]],
    ) -> None:
        panel, _reported = build(layout_config)
        sources = folder("sources", holds=3)
        panel.update_view(view(sources))
        panel.stems_list.toggle_folder(sources.key)

        click_row_name(panel.stems_list.tags, sources.key, kind=CLICKED, button=dpg.mvMouseButton_Right)

        assert LANGUAGE_MANAGER["main.converter.label.context_close_folder"] in [item["label"] for item in registered]

    def test_a_folder_removed_from_its_menu_takes_everything_it_holds(
        self,
        dpg_context: None,
        layout_config: LayoutConfig,
        registered: List[Dict[str, Any]],
    ) -> None:
        panel, _reported = build(layout_config)
        folders: List[Path] = []
        panel.on_folder_removed = folders.append
        sources = folder("sources", holds=3)
        panel.update_view(view(sources))

        click_row_name(panel.stems_list.tags, sources.key, kind=CLICKED, button=dpg.mvMouseButton_Right)
        removal = next(
            item
            for item in registered
            if item["label"] == LANGUAGE_MANAGER["main.converter.label.context_remove_folder"]
        )
        removal["callback"]()

        assert folders == [sources.path]


class TestTheMovesAMixOffers(BaseTestSuite):
    """A run mixing its recordings orders them, so a row's menu offers the moves that reorder it."""

    @staticmethod
    def _label(element: ConverterStemMoveElements) -> str:
        return LANGUAGE_MANAGER[Page.MAIN, Panel.CONVERTER, TextType.LABEL, element]

    @classmethod
    def _offered(
        cls,
        panel: GUIConverterPanel,
        entry: StemRowViewModel,
        registered: List[Dict[str, Any]],
    ) -> Dict[str, Dict[str, Any]]:
        """The move items the row's menu registers, each under the label it prints."""
        right_click(panel, entry)
        offered = {cls._label(element) for element in ConverterStemMoveElements}
        return {item["label"]: item for item in registered if item["label"] in offered}

    @classmethod
    def _moves(
        cls,
        panel: GUIConverterPanel,
        entry: StemRowViewModel,
        registered: List[Dict[str, Any]],
    ) -> Dict[str, bool]:
        """The moves the row's menu offers and whether each stands live, in the order it lists them."""
        offered = cls._offered(panel, entry, registered)
        return {label: bool(item.get("enabled", True)) for label, item in offered.items()}

    def test_a_run_writing_one_reconstruction_apiece_offers_removal_alone(
        self,
        dpg_context: None,
        layout_config: LayoutConfig,
        registered: List[Dict[str, Any]],
    ) -> None:
        panel, _reported = build(layout_config)
        kick = row("kick")
        panel.update_view(view(kick, row("snare")))

        moves = self._moves(panel, kick, registered)

        assert list(moves) == [self._label(ConverterStemMoveElements.CONTEXT_REMOVE_STEM)]

    def test_a_mix_offers_every_move_a_row_can_make(
        self,
        dpg_context: None,
        layout_config: LayoutConfig,
        registered: List[Dict[str, Any]],
    ) -> None:
        panel, _reported = build(layout_config)
        kick = row("kick")
        panel.update_view(view(kick, row("snare"), output=OutputKind.MIXED))

        moves = self._moves(panel, kick, registered)

        assert list(moves) == [
            self._label(ConverterStemMoveElements.CONTEXT_MOVE_UP),
            self._label(ConverterStemMoveElements.CONTEXT_MOVE_DOWN),
            self._label(ConverterStemMoveElements.CONTEXT_JOIN_ABOVE),
            self._label(ConverterStemMoveElements.CONTEXT_JOIN_BELOW),
            self._label(ConverterStemMoveElements.CONTEXT_ISOLATE),
            self._label(ConverterStemMoveElements.CONTEXT_REMOVE_STEM),
        ]

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        """One row's placement among the levels, and the moves that placement leaves it."""

        rows: Tuple[StemRowViewModel, ...]
        subject: int
        expected: Dict[ConverterStemMoveElements, bool]

    test_cases = (
        TestCase(
            label="alone_on_the_first_of_two_levels",
            rows=(row("kick", level=0, level_count=2), row("snare", level=1, level_count=2)),
            subject=0,
            expected={
                ConverterStemMoveElements.CONTEXT_MOVE_UP: False,
                ConverterStemMoveElements.CONTEXT_MOVE_DOWN: False,
                ConverterStemMoveElements.CONTEXT_JOIN_ABOVE: False,
                ConverterStemMoveElements.CONTEXT_JOIN_BELOW: True,
                ConverterStemMoveElements.CONTEXT_ISOLATE: False,
            },
        ),
        TestCase(
            label="second_on_the_last_of_two_levels",
            rows=(
                row("hat", level=0, level_count=2),
                row("kick", level=1, position=0, level_size=2, level_count=2),
                row("snare", level=1, position=1, level_size=2, level_count=2),
            ),
            subject=2,
            expected={
                ConverterStemMoveElements.CONTEXT_MOVE_UP: True,
                ConverterStemMoveElements.CONTEXT_MOVE_DOWN: False,
                ConverterStemMoveElements.CONTEXT_JOIN_ABOVE: True,
                ConverterStemMoveElements.CONTEXT_JOIN_BELOW: False,
                ConverterStemMoveElements.CONTEXT_ISOLATE: True,
            },
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_each_move_stands_live_where_the_row_has_room_for_it(
        self,
        test_case: TestCase,
        dpg_context: None,
        layout_config: LayoutConfig,
        registered: List[Dict[str, Any]],
    ) -> None:
        panel, _reported = build(layout_config)
        panel.update_view(view(*test_case.rows, output=OutputKind.MIXED))

        moves = self._moves(panel, test_case.rows[test_case.subject], registered)

        expected = {self._label(element): live for element, live in test_case.expected.items()}
        assert {label: moves[label] for label in expected} == expected

    def test_each_move_reports_the_direction_it_prints(
        self,
        dpg_context: None,
        layout_config: LayoutConfig,
        registered: List[Dict[str, Any]],
    ) -> None:
        """An offset is added to the row's place, so moving earlier reports -1 and later reports 1.

        The item is fired rather than read, since a move standing under the right label still
        reorders the wrong way while the offset behind it is the mirror of what the label says.
        """
        panel, _reported = build(layout_config)
        moved: List[Tuple[Path, int]] = []
        joined: List[Tuple[Path, int]] = []
        isolated: List[Path] = []
        panel.on_source_moved = lambda path, offset: moved.append((path, offset))
        panel.on_source_level_joined = lambda path, offset: joined.append((path, offset))
        panel.on_source_isolated = isolated.append
        kick = row("kick", level=1, position=0, level_size=2, level_count=3)
        snare = row("snare", level=1, position=1, level_size=2, level_count=3)
        panel.update_view(view(row("hat", level=0, level_count=3), kick, snare, output=OutputKind.MIXED))

        offered = self._offered(panel, snare, registered)
        for element in (
            ConverterStemMoveElements.CONTEXT_MOVE_UP,
            ConverterStemMoveElements.CONTEXT_MOVE_DOWN,
            ConverterStemMoveElements.CONTEXT_JOIN_ABOVE,
            ConverterStemMoveElements.CONTEXT_JOIN_BELOW,
            ConverterStemMoveElements.CONTEXT_ISOLATE,
        ):
            offered[self._label(element)]["callback"]()

        assert moved == [(snare.path, -1), (snare.path, 1)]
        assert joined == [(snare.path, -1), (snare.path, 1)]
        assert isolated == [snare.path]


class TestTheRemovalItemInTheMenu:
    """Taking a row out is one action, so the item and the key print and reach the same thing."""

    @staticmethod
    def _removal(
        panel: GUIConverterPanel,
        entry: StemRowViewModel,
        registered: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """The removal item the row's menu prints, reached the way a reader reaches it."""
        label = LANGUAGE_MANAGER["main.converter.label.context_remove_stem"]
        right_click(panel, entry)
        return next(item for item in registered if item["label"] == label)

    def test_it_takes_the_recording_it_stands_over_and_nothing_else(
        self,
        dpg_context: None,
        layout_config: LayoutConfig,
        registered: List[Dict[str, Any]],
    ) -> None:
        """The item is fired, since a removal printing the right key still reaches nothing."""
        panel, _reported = build(layout_config)
        removed: List[Path] = []
        folders: List[Path] = []
        panel.on_source_removed = removed.append
        panel.on_folder_removed = folders.append
        kick = row("kick")
        panel.update_view(view(kick, row("snare")))

        self._removal(panel, kick, registered)["callback"]()

        assert removed == [kick.path]
        assert folders == []

    def test_it_prints_the_key_that_does_the_same_thing(
        self,
        dpg_context: None,
        layout_config: LayoutConfig,
        registered: List[Dict[str, Any]],
    ) -> None:
        panel, _reported = build(layout_config)
        kick = row("kick")
        panel.update_view(view(kick, row("snare")))

        removal = self._removal(panel, kick, registered)

        assert removal["shortcut"] == shipped_source().display(ShortcutId.SOURCES_REMOVE_SOURCE)

    def test_it_prints_whatever_the_scheme_in_place_gives_the_action(
        self,
        dpg_context: None,
        layout_config: LayoutConfig,
        registered: List[Dict[str, Any]],
    ) -> None:
        """A rebind reaches the menu, which is what tells the printed key from a written one."""
        source = rebound_source(ShortcutId.SOURCES_REMOVE_SOURCE, REBOUND_REMOVAL)
        panel, _reported = build(layout_config, shortcut_source=source)
        kick = row("kick")
        panel.update_view(view(kick, row("snare")))

        removal = self._removal(panel, kick, registered)

        assert removal["shortcut"] == REBOUND_REMOVAL
        assert removal["shortcut"] != shipped_source().display(ShortcutId.SOURCES_REMOVE_SOURCE)

    def test_it_stands_inert_while_a_run_holds_the_list(
        self,
        dpg_context: None,
        layout_config: LayoutConfig,
        registered: List[Dict[str, Any]],
    ) -> None:
        panel, _reported = build(layout_config)
        kick = row("kick")
        panel.update_view(view(kick, row("snare"), phase=ConversionPhase.RUNNING))

        removal = self._removal(panel, kick, registered)

        assert removal["enabled"] is False
