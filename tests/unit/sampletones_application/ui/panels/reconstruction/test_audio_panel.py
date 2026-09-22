from typing import Iterator, List, Optional

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
from sampletones_application.tags.general import SUF_HANDLER_REGISTRY
from sampletones_application.tags.reconstructions import (
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_INPUT_NES_FREQUENCY,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_TOOLTIP_NES_FREQUENCY,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_TOOLTIP_NES_FREQUENCY_LOCKED,
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
from sampletones_shared.constants.nes import MAX_NES_FREQUENCY, NTSC_FREQUENCY, PAL_FREQUENCY

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


def _view_model(
    nes_frequency: Optional[int],
    *,
    file_state: ReconstructionPathState = ReconstructionPathState.AVAILABLE,
) -> ReconstructionViewModel:
    empty_path = ReconstructionPathViewModel(state=ReconstructionPathState.EMPTY, paths=())
    loaded = nes_frequency is not None
    return ReconstructionViewModel(
        reconstruction_loaded=loaded,
        playing_channels=frozenset(),
        selected_channels=frozenset(),
        reconstruction_file=(ReconstructionPathViewModel(state=file_state, paths=()) if loaded else empty_path),
        original_audio=empty_path,
        nes_frequency=nes_frequency,
    )


def _commit(rendered_panel: GUIReconstructionAudioPanel, value: int) -> None:
    """Types a value into the field and finishes the edit the way DearPyGui reports it."""
    dpg.set_value(TAG_RECONSTRUCTIONS_RECONSTRUCTION_INPUT_NES_FREQUENCY, value)
    handler = dpg.get_item_children(
        compose_tag(TAG_RECONSTRUCTIONS_RECONSTRUCTION_INPUT_NES_FREQUENCY, SUF_HANDLER_REGISTRY),
        1,
    )[0]
    dpg.get_item_callback(handler)(TAG_RECONSTRUCTIONS_RECONSTRUCTION_INPUT_NES_FREQUENCY, value)


class TestEngineRateField:
    """The rate the card states for the open reconstruction, which a reader can change."""

    def test_a_loaded_reconstruction_states_its_rate(
        self,
        rendered_panel: GUIReconstructionAudioPanel,
    ) -> None:
        rendered_panel.update_view(_view_model(PAL_FREQUENCY))

        assert dpg.get_value(TAG_RECONSTRUCTIONS_RECONSTRUCTION_INPUT_NES_FREQUENCY) == PAL_FREQUENCY

    def test_an_empty_tab_shows_no_field(
        self,
        rendered_panel: GUIReconstructionAudioPanel,
    ) -> None:
        rendered_panel.update_view(_view_model(PAL_FREQUENCY))
        rendered_panel.update_view(_view_model(None))

        assert not dpg.is_item_shown(TAG_RECONSTRUCTIONS_RECONSTRUCTION_INPUT_NES_FREQUENCY)

    def test_the_rate_reads_as_a_monospaced_figure(
        self,
        rendered_panel: GUIReconstructionAudioPanel,
    ) -> None:
        field = dpg.get_item_info(TAG_RECONSTRUCTIONS_RECONSTRUCTION_INPUT_NES_FREQUENCY)

        assert field["font"] == FontRegistry.get_tag(Font.MONO)

    def test_a_document_with_a_file_takes_a_new_rate(
        self,
        rendered_panel: GUIReconstructionAudioPanel,
    ) -> None:
        rendered_panel.update_view(_view_model(PAL_FREQUENCY))

        assert dpg.get_item_configuration(TAG_RECONSTRUCTIONS_RECONSTRUCTION_INPUT_NES_FREQUENCY)["enabled"]
        assert dpg.get_item_configuration(TAG_RECONSTRUCTIONS_RECONSTRUCTION_TOOLTIP_NES_FREQUENCY)["show"]
        assert not dpg.get_item_configuration(TAG_RECONSTRUCTIONS_RECONSTRUCTION_TOOLTIP_NES_FREQUENCY_LOCKED)["show"]

    def test_a_document_detached_from_its_file_locks_the_field_and_says_why(
        self,
        rendered_panel: GUIReconstructionAudioPanel,
    ) -> None:
        rendered_panel.update_view(_view_model(PAL_FREQUENCY, file_state=ReconstructionPathState.NOT_APPLICABLE))

        assert dpg.is_item_shown(TAG_RECONSTRUCTIONS_RECONSTRUCTION_INPUT_NES_FREQUENCY)
        assert not dpg.get_item_configuration(TAG_RECONSTRUCTIONS_RECONSTRUCTION_INPUT_NES_FREQUENCY)["enabled"]
        assert not dpg.get_item_configuration(TAG_RECONSTRUCTIONS_RECONSTRUCTION_TOOLTIP_NES_FREQUENCY)["show"]
        assert dpg.get_item_configuration(TAG_RECONSTRUCTIONS_RECONSTRUCTION_TOOLTIP_NES_FREQUENCY_LOCKED)["show"]

    def test_the_lock_lifts_when_a_document_with_a_file_opens(
        self,
        rendered_panel: GUIReconstructionAudioPanel,
    ) -> None:
        rendered_panel.update_view(_view_model(PAL_FREQUENCY, file_state=ReconstructionPathState.NOT_APPLICABLE))
        rendered_panel.update_view(_view_model(NTSC_FREQUENCY))

        assert dpg.get_item_configuration(TAG_RECONSTRUCTIONS_RECONSTRUCTION_INPUT_NES_FREQUENCY)["enabled"]
        assert dpg.get_item_configuration(TAG_RECONSTRUCTIONS_RECONSTRUCTION_TOOLTIP_NES_FREQUENCY)["show"]
        assert not dpg.get_item_configuration(TAG_RECONSTRUCTIONS_RECONSTRUCTION_TOOLTIP_NES_FREQUENCY_LOCKED)["show"]

    def test_a_finished_edit_reports_the_rate_typed(
        self,
        rendered_panel: GUIReconstructionAudioPanel,
    ) -> None:
        reported: List[int] = []
        rendered_panel.on_nes_frequency_changed = reported.append
        rendered_panel.update_view(_view_model(NTSC_FREQUENCY))

        _commit(rendered_panel, PAL_FREQUENCY)

        assert reported == [PAL_FREQUENCY]

    def test_a_rate_out_of_range_is_reported_at_the_nearest_bound(
        self,
        rendered_panel: GUIReconstructionAudioPanel,
    ) -> None:
        reported: List[int] = []
        rendered_panel.on_nes_frequency_changed = reported.append
        rendered_panel.update_view(_view_model(NTSC_FREQUENCY))

        _commit(rendered_panel, MAX_NES_FREQUENCY + 1)

        assert reported == [MAX_NES_FREQUENCY]
