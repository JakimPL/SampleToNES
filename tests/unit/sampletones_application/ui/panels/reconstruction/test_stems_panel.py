from pathlib import Path
from typing import FrozenSet, Iterator, List, Tuple

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
from sampletones_application.tags.general import SUF_CHECKBOX, SUF_TEXT
from sampletones_application.tags.reconstructions import (
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_CHECKBOX_COLLAPSE_LEVELS,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_TEXT_STEMS_EMPTY,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_TEXT_STEMS_SETUP,
)
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.panels.reconstruction.stems import (
    GUIReconstructionStemsPanel,
)
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.ui.themes.setup import setup_themes
from sampletones_application.utils.palette.catalog import PaletteCatalog
from sampletones_application.utils.palette.source import PaletteSource
from sampletones_application.view_model.reconstruction.stems import (
    ReconstructionStemsViewModel,
)
from sampletones_application.view_model.shared.stems import (
    StemRowViewModel,
    StemsListViewModel,
)
from sampletones_core.constants.enums import ChannelName, HierarchyMode

ROOT_TAG = "test_root"
CHANNELS: Tuple[ChannelName, ...] = (ChannelName.PULSE1, ChannelName.NOISE)


@pytest.fixture
def layout_config() -> LayoutConfig:
    source = PaletteSource(PaletteCatalog.load(PALETTES_DIRECTORY).default)
    return load_layout_config(LAYOUT_DIRECTORY, BEHAVIOR_DIRECTORY, source)


@pytest.fixture
def dpg_context(layout_config: LayoutConfig) -> Iterator[None]:
    """Stands up the context, fonts, themes, and section-header geometry the panel resolves on construction."""
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


@pytest.fixture
def panel(dpg_context: None, layout_config: LayoutConfig) -> GUIReconstructionStemsPanel:
    return GUIReconstructionStemsPanel(
        stems_layout=layout_config.general.stems,
        language_manager=LanguageManager(LANG_EN),
        status_bar=GUIStatusBar(),
    )


def render(panel: GUIReconstructionStemsPanel) -> None:
    with dpg.window(tag=ROOT_TAG):
        panel.create_panel(ROOT_TAG)


def _row(
    stem_id: int,
    *,
    name: str,
    channels: FrozenSet[ChannelName] = frozenset(CHANNELS),
    offered_channels: FrozenSet[ChannelName] = frozenset(CHANNELS),
    level: int = 0,
    position: int = 0,
    level_size: int = 1,
    level_count: int = 1,
) -> StemRowViewModel:
    return StemRowViewModel(
        key=str(stem_id),
        path=Path(f"/audio/{name}.wav"),
        channels=channels,
        offered_channels=offered_channels,
        available=True,
        level=level,
        position=position,
        level_size=level_size,
        level_count=level_count,
    )


def _view_model(
    *rows: StemRowViewModel,
    hierarchy_mode: HierarchyMode | None = None,
    muted_channels: FrozenSet[ChannelName] = frozenset(),
) -> ReconstructionStemsViewModel:
    return ReconstructionStemsViewModel(
        reconstruction_loaded=True,
        stems=StemsListViewModel(
            rows=rows,
            channels_in_play=CHANNELS if rows else (),
            muted_channels=muted_channels,
            live=True,
            collapse_levels=False,
        ),
        hierarchy_mode=hierarchy_mode,
        channel_cap=2 if hierarchy_mode is not None else None,
    )


class TestStemsPanelRows:
    def test_one_row_per_recording(self, panel: GUIReconstructionStemsPanel) -> None:
        render(panel)

        panel.update_view(_view_model(_row(0, name="kick"), _row(1, name="snare")))

        stems_list = panel.stems_list
        assert dpg.get_item_label(stems_list.row_tag("0", SUF_TEXT)) == "kick"
        assert dpg.get_item_label(stems_list.row_tag("1", SUF_TEXT)) == "snare"

    def test_a_row_offers_a_box_on_every_channel_its_recording_holds(
        self,
        panel: GUIReconstructionStemsPanel,
    ) -> None:
        render(panel)

        panel.update_view(_view_model(_row(0, name="kick", offered_channels=frozenset({ChannelName.PULSE1}))))

        stems_list = panel.stems_list
        assert dpg.does_item_exist(stems_list.channel_tag("0", ChannelName.PULSE1))
        assert not dpg.does_item_exist(stems_list.channel_tag("0", ChannelName.NOISE))

    def test_every_row_carries_a_master_box(self, panel: GUIReconstructionStemsPanel) -> None:
        render(panel)

        panel.update_view(_view_model(_row(0, name="kick")))

        assert dpg.get_value(panel.stems_list.row_tag("0", SUF_CHECKBOX))

    def test_rows_follow_a_changed_recording_set(self, panel: GUIReconstructionStemsPanel) -> None:
        render(panel)
        panel.update_view(_view_model(_row(0, name="kick"), _row(1, name="snare")))

        panel.update_view(_view_model(_row(1, name="snare")))

        stems_list = panel.stems_list
        assert not dpg.does_item_exist(stems_list.row_tag("0", SUF_TEXT))
        assert dpg.does_item_exist(stems_list.row_tag("1", SUF_TEXT))


class TestStemsPanelSelection:
    def test_unticking_a_channel_reports_the_recording_and_what_it_keeps(
        self,
        panel: GUIReconstructionStemsPanel,
    ) -> None:
        reported: List[Tuple[int, FrozenSet[ChannelName]]] = []
        panel.on_stem_channels_changed = lambda stem_id, channels: reported.append((stem_id, channels))
        render(panel)
        panel.update_view(_view_model(_row(0, name="kick")))

        noise_tag = panel.stems_list.channel_tag("0", ChannelName.NOISE)
        dpg.set_value(noise_tag, False)
        dpg.get_item_callback(noise_tag)(noise_tag, False, ("0", ChannelName.NOISE))

        assert reported == [(0, frozenset({ChannelName.PULSE1}))]

    def test_unticking_the_master_box_silences_the_recording_everywhere(
        self,
        panel: GUIReconstructionStemsPanel,
    ) -> None:
        reported: List[Tuple[int, FrozenSet[ChannelName]]] = []
        panel.on_stem_channels_changed = lambda stem_id, channels: reported.append((stem_id, channels))
        render(panel)
        panel.update_view(_view_model(_row(0, name="kick")))

        master_tag = panel.stems_list.row_tag("0", SUF_CHECKBOX)
        dpg.get_item_callback(master_tag)(master_tag, False, "0")

        assert reported == [(0, frozenset())]


class TestStemsPanelLevels:
    def test_the_collapse_toggle_appears_once_there_are_levels_to_collapse(
        self,
        panel: GUIReconstructionStemsPanel,
    ) -> None:
        render(panel)

        panel.update_view(_view_model(_row(0, name="kick")))
        assert not dpg.is_item_shown(TAG_RECONSTRUCTIONS_RECONSTRUCTION_CHECKBOX_COLLAPSE_LEVELS)

        panel.update_view(
            _view_model(
                _row(0, name="kick", level=0, level_count=2),
                _row(1, name="snare", level=1, level_count=2),
            )
        )
        assert dpg.is_item_shown(TAG_RECONSTRUCTIONS_RECONSTRUCTION_CHECKBOX_COLLAPSE_LEVELS)

    def test_collapsing_redraws_the_rows_in_one_table(self, panel: GUIReconstructionStemsPanel) -> None:
        render(panel)
        panel.update_view(
            _view_model(
                _row(0, name="kick", level=0, level_count=2),
                _row(1, name="snare", level=1, level_count=2),
            )
        )

        dpg.set_value(TAG_RECONSTRUCTIONS_RECONSTRUCTION_CHECKBOX_COLLAPSE_LEVELS, True)
        dpg.get_item_callback(TAG_RECONSTRUCTIONS_RECONSTRUCTION_CHECKBOX_COLLAPSE_LEVELS)(
            TAG_RECONSTRUCTIONS_RECONSTRUCTION_CHECKBOX_COLLAPSE_LEVELS,
            True,
        )

        assert dpg.does_item_exist(panel.stems_list.table_tag)
        assert dpg.does_item_exist(panel.stems_list.row_tag("1", SUF_TEXT))

    def test_a_reader_who_collapsed_the_levels_keeps_them_collapsed_across_an_edit(
        self,
        panel: GUIReconstructionStemsPanel,
    ) -> None:
        render(panel)
        panel.update_view(
            _view_model(
                _row(0, name="kick", level=0, level_count=2),
                _row(1, name="snare", level=1, level_count=2),
            )
        )
        dpg.set_value(TAG_RECONSTRUCTIONS_RECONSTRUCTION_CHECKBOX_COLLAPSE_LEVELS, True)

        panel.update_view(
            _view_model(
                _row(0, name="kick", level=0, level_count=2),
                _row(2, name="hat", level=1, level_count=2),
            )
        )

        assert dpg.does_item_exist(panel.stems_list.table_tag)


class TestStemsPanelStates:
    def test_the_setup_line_states_mode_and_cap(self, panel: GUIReconstructionStemsPanel) -> None:
        render(panel)

        panel.update_view(_view_model(_row(0, name="kick"), hierarchy_mode=HierarchyMode.STRICT))

        assert dpg.is_item_shown(TAG_RECONSTRUCTIONS_RECONSTRUCTION_TEXT_STEMS_SETUP)
        assert "Strict" in dpg.get_value(TAG_RECONSTRUCTIONS_RECONSTRUCTION_TEXT_STEMS_SETUP)
        assert "2" in dpg.get_value(TAG_RECONSTRUCTIONS_RECONSTRUCTION_TEXT_STEMS_SETUP)

    def test_the_empty_state_shows_for_a_loaded_reconstruction_without_source(
        self,
        panel: GUIReconstructionStemsPanel,
    ) -> None:
        render(panel)

        panel.update_view(_view_model())

        assert dpg.is_item_shown(TAG_RECONSTRUCTIONS_RECONSTRUCTION_TEXT_STEMS_EMPTY)
        assert not dpg.is_item_shown(TAG_RECONSTRUCTIONS_RECONSTRUCTION_TEXT_STEMS_SETUP)
        assert not dpg.is_item_shown(panel.stems_list.tag)
