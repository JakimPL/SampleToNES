from typing import Iterator

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
from sampletones_application.tags.reconstructions import (
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_TEXT_STEMS_EMPTY,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_TEXT_STEMS_SETUP,
)
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.panels.reconstruction.stems import (
    GUIReconstructionStemsPanel,
)
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.ui.themes.setup import setup_themes
from sampletones_application.utils.palette.catalog import PaletteCatalog
from sampletones_application.utils.palette.source import PaletteSource
from sampletones_application.view_model.reconstruction.stems import (
    ReconstructionStemsViewModel,
    StemViewModel,
)
from sampletones_core.constants.enums import ChannelName, HierarchyMode

ROOT_TAG = "test_root"


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
def panel(dpg_context: None) -> GUIReconstructionStemsPanel:
    return GUIReconstructionStemsPanel(language_manager=LanguageManager(LANG_EN))


def render(panel: GUIReconstructionStemsPanel) -> None:
    with dpg.window(tag=ROOT_TAG):
        panel.create_panel(ROOT_TAG)


def _stem_row(stem_id: int, *, label: str, selected: bool, enabled: bool) -> StemViewModel:
    return StemViewModel(
        stem_id=stem_id,
        label=label,
        channels=(ChannelName.PULSE1, ChannelName.NOISE),
        enabled=enabled,
        selected=selected,
    )


def _view_model(*rows: StemViewModel, hierarchy_mode=None) -> ReconstructionStemsViewModel:
    return ReconstructionStemsViewModel(
        reconstruction_loaded=True,
        stems=rows,
        hierarchy_mode=hierarchy_mode,
        channel_cap=2 if hierarchy_mode is not None else None,
    )


class TestStemsPanelRows:
    def test_one_checkbox_row_per_stem(self, panel: GUIReconstructionStemsPanel) -> None:
        render(panel)

        panel.update_view(
            _view_model(
                _stem_row(0, label="kick.wav", selected=True, enabled=True),
                _stem_row(1, label="snare.wav", selected=True, enabled=True),
            )
        )

        kick_tag = GUIReconstructionStemsPanel._stem_checkbox_tag(0)
        snare_tag = GUIReconstructionStemsPanel._stem_checkbox_tag(1)
        assert dpg.does_item_exist(kick_tag)
        assert dpg.does_item_exist(snare_tag)
        assert dpg.get_value(kick_tag)
        assert dpg.get_value(snare_tag)
        assert dpg.get_item_label(kick_tag) == "kick.wav"

    def test_a_stem_without_assigned_frames_is_disabled(self, panel: GUIReconstructionStemsPanel) -> None:
        render(panel)

        panel.update_view(
            _view_model(
                _stem_row(0, label="kick.wav", selected=False, enabled=False),
            )
        )

        assert not dpg.is_item_enabled(GUIReconstructionStemsPanel._stem_checkbox_tag(0))

    def test_rows_follow_a_changed_stem_set(self, panel: GUIReconstructionStemsPanel) -> None:
        render(panel)
        panel.update_view(
            _view_model(
                _stem_row(0, label="kick.wav", selected=True, enabled=True),
                _stem_row(1, label="snare.wav", selected=True, enabled=True),
            )
        )

        panel.update_view(
            _view_model(
                _stem_row(1, label="snare.wav", selected=True, enabled=True),
            )
        )

        assert not dpg.does_item_exist(GUIReconstructionStemsPanel._stem_checkbox_tag(0))
        assert dpg.does_item_exist(GUIReconstructionStemsPanel._stem_checkbox_tag(1))

    def test_a_reused_row_takes_the_new_stem_label(self, panel: GUIReconstructionStemsPanel) -> None:
        render(panel)
        panel.update_view(
            _view_model(
                _stem_row(0, label="kick.wav", selected=True, enabled=True),
            )
        )

        panel.update_view(
            _view_model(
                _stem_row(0, label="snare.wav", selected=True, enabled=True),
            )
        )

        assert dpg.get_item_label(GUIReconstructionStemsPanel._stem_checkbox_tag(0)) == "snare.wav"


class TestStemsPanelSelection:
    def test_unchecking_a_stem_reports_the_remaining_selection(self, panel: GUIReconstructionStemsPanel) -> None:
        selections = []
        panel.on_stems_changed = selections.append
        render(panel)
        panel.update_view(
            _view_model(
                _stem_row(0, label="kick.wav", selected=True, enabled=True),
                _stem_row(1, label="snare.wav", selected=True, enabled=True),
            )
        )

        kick_tag = GUIReconstructionStemsPanel._stem_checkbox_tag(0)
        dpg.set_value(kick_tag, False)
        dpg.get_item_callback(kick_tag)(kick_tag, False)

        assert selections == [frozenset({1})]


class TestStemsPanelStates:
    def test_the_setup_line_states_mode_and_cap(self, panel: GUIReconstructionStemsPanel) -> None:
        render(panel)

        panel.update_view(
            _view_model(
                _stem_row(0, label="kick.wav", selected=True, enabled=True),
                hierarchy_mode=HierarchyMode.STRICT,
            )
        )

        assert dpg.is_item_shown(TAG_RECONSTRUCTIONS_RECONSTRUCTION_TEXT_STEMS_SETUP)
        assert "Strict" in dpg.get_value(TAG_RECONSTRUCTIONS_RECONSTRUCTION_TEXT_STEMS_SETUP)
        assert "2" in dpg.get_value(TAG_RECONSTRUCTIONS_RECONSTRUCTION_TEXT_STEMS_SETUP)

    def test_the_empty_state_shows_for_a_loaded_reconstruction_without_source(
        self, panel: GUIReconstructionStemsPanel
    ) -> None:
        render(panel)

        panel.update_view(_view_model())

        assert dpg.is_item_shown(TAG_RECONSTRUCTIONS_RECONSTRUCTION_TEXT_STEMS_EMPTY)
        assert not dpg.is_item_shown(TAG_RECONSTRUCTIONS_RECONSTRUCTION_TEXT_STEMS_SETUP)
