from typing import Iterator, Optional

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
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_TEXT_NES_FREQUENCY,
)
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.panels.reconstruction.audio import (
    GUIReconstructionAudioPanel,
)
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.ui.themes.setup import setup_themes
from sampletones_application.utils.palette.catalog import PaletteCatalog
from sampletones_application.utils.palette.source import PaletteSource
from sampletones_application.view_model.reconstruction.paths.path import (
    ReconstructionPathViewModel,
)
from sampletones_application.view_model.reconstruction.paths.state import (
    ReconstructionPathState,
)
from sampletones_application.view_model.reconstruction.reconstruction import (
    ReconstructionViewModel,
)
from sampletones_core.configs.display import format_nes_frequency
from sampletones_shared.constants.nes import PAL_FREQUENCY

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
def panel(dpg_context: None, layout_config: LayoutConfig) -> GUIReconstructionAudioPanel:
    return GUIReconstructionAudioPanel(
        path_colors=layout_config.general.colors.paths,
        path_status_color=layout_config.general.colors.text.disabled,
        language_manager=LanguageManager(LANG_EN),
        status_bar=GUIStatusBar(),
    )


@pytest.fixture
def rendered_panel(panel: GUIReconstructionAudioPanel) -> GUIReconstructionAudioPanel:
    with dpg.window(tag=ROOT_TAG):
        panel.create_panel(ROOT_TAG)

    return panel


def _view_model(nes_frequency: Optional[int]) -> ReconstructionViewModel:
    empty_path = ReconstructionPathViewModel(state=ReconstructionPathState.EMPTY, paths=())
    return ReconstructionViewModel(
        reconstruction_loaded=nes_frequency is not None,
        playing_channels=frozenset(),
        selected_channels=frozenset(),
        reconstruction_file=empty_path,
        original_audio=empty_path,
        nes_frequency=nes_frequency,
    )


class TestEngineRateReadout:
    """The rate the card states for the open reconstruction."""

    def test_a_loaded_reconstruction_states_its_rate(
        self,
        rendered_panel: GUIReconstructionAudioPanel,
    ) -> None:
        rendered_panel.update_view(_view_model(PAL_FREQUENCY))

        assert dpg.get_value(TAG_RECONSTRUCTIONS_RECONSTRUCTION_TEXT_NES_FREQUENCY) == format_nes_frequency(
            PAL_FREQUENCY,
        )

    def test_an_empty_tab_leaves_the_readout_blank(
        self,
        rendered_panel: GUIReconstructionAudioPanel,
    ) -> None:
        rendered_panel.update_view(_view_model(PAL_FREQUENCY))
        rendered_panel.update_view(_view_model(None))

        assert dpg.get_value(TAG_RECONSTRUCTIONS_RECONSTRUCTION_TEXT_NES_FREQUENCY) == ""

    def test_the_rate_reads_as_a_monospaced_figure(
        self,
        rendered_panel: GUIReconstructionAudioPanel,
    ) -> None:
        readout = dpg.get_item_info(TAG_RECONSTRUCTIONS_RECONSTRUCTION_TEXT_NES_FREQUENCY)

        assert readout["font"] == FontRegistry.get_tag(Font.MONO)
