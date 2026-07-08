from typing import Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.instructions import (
    InstructionPanelElements,
)
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.general import (
    SUF_PANEL_CENTER,
    TAG_GLOBAL_TAB_INSTRUCTIONS,
    TAG_GLOBAL_THEME_PANEL_SURFACE,
)
from sampletones_application.constants.instructions import (
    SUF_GRAPH_INSTRUCTIONS_INSTRUCTION_WAVEFORM_WINDOW,
    SUF_GRAPH_INSTRUCTIONS_INSTRUCTIONS_SPECTRUM_WINDOW,
    TAG_INSTRUCTIONS_INSTRUCTION_PANEL,
    TAG_INSTRUCTIONS_INSTRUCTION_PANEL_SPECTRUM,
    TAG_INSTRUCTIONS_INSTRUCTION_PANEL_WAVEFORM,
)
from sampletones_application.layout.general import GeneralLayout
from sampletones_application.layout.graphs import GraphsLayout
from sampletones_application.ui.elements.graphs.spectrum import GUISpectrumGraph
from sampletones_application.ui.elements.graphs.waveform import GUIWaveformGraph
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.panels.player import GUIAudioPlayerPanel
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.view_model.instruction.data import InstructionPanelData
from sampletones_shared.exceptions import LibraryDisplayError
from sampletones_shared.logger import logger
from sampletones_shared.types.callback import VoidCallback


class GUIInstructionPanel(GUIPanel):
    def __init__(
        self,
        player_panel: GUIAudioPlayerPanel,
        *,
        layout: GraphsLayout,
        general_layout: GeneralLayout,
        language_manager: LanguageManager,
        status_bar: GUIStatusBar,
    ) -> None:
        self._player_panel = player_panel
        self._layout = layout
        self._general_layout = general_layout
        self._language_manager = language_manager
        self._status_bar = status_bar
        self.waveform_display: GUIWaveformGraph
        self.spectrum_display: GUISpectrumGraph

        self.on_clear_instruction_details: Optional[VoidCallback] = None

        self._lbl_waveform = language_manager[
            Page.INSTRUCTIONS,
            Panel.INSTRUCTION,
            TextType.LABEL,
            InstructionPanelElements.WAVEFORM_LABEL,
        ]
        self._lbl_spectrum = language_manager[
            Page.INSTRUCTIONS,
            Panel.INSTRUCTION,
            TextType.LABEL,
            InstructionPanelElements.SPECTRUM_LABEL,
        ]

        self.waveform_tag = f"{TAG_INSTRUCTIONS_INSTRUCTION_PANEL}{SUF_GRAPH_INSTRUCTIONS_INSTRUCTION_WAVEFORM_WINDOW}"
        self.spectrum_tag = f"{TAG_INSTRUCTIONS_INSTRUCTION_PANEL}{SUF_GRAPH_INSTRUCTIONS_INSTRUCTIONS_SPECTRUM_WINDOW}"

        super().__init__(
            tag=TAG_INSTRUCTIONS_INSTRUCTION_PANEL,
            parent=f"{TAG_GLOBAL_TAB_INSTRUCTIONS}{SUF_PANEL_CENTER}",
        )

    def create_panel(self) -> None:
        self._create_player_panel()
        dpg.add_spacer(height=self._general_layout.panel_gap, parent=self.parent)
        self._create_waveform_display()
        dpg.add_spacer(height=self._general_layout.panel_gap, parent=self.parent)
        self._create_spectrum_display()

        surface_theme = ThemeRegistry.get(TAG_GLOBAL_THEME_PANEL_SURFACE)
        surface_theme.bind_to_item(self.waveform_tag)
        surface_theme.bind_to_item(self.spectrum_tag)

    def _create_waveform_display(self) -> None:
        with dpg.child_window(
            tag=self.waveform_tag,
            parent=self.parent,
            no_scrollbar=True,
            auto_resize_y=True,
            border=True,
        ):
            self._create_section_header(
                self._lbl_waveform,
                glyph=self._glyphs.headers.waveform,
            )
            self.waveform_display = GUIWaveformGraph(
                tag=TAG_INSTRUCTIONS_INSTRUCTION_PANEL_WAVEFORM,
                parent=self.waveform_tag,
                layout=self._layout,
                language_manager=self._language_manager,
                status_bar=self._status_bar,
            )

    def _create_spectrum_display(self) -> None:
        with dpg.child_window(
            tag=self.spectrum_tag,
            parent=self.parent,
            no_scrollbar=True,
            auto_resize_y=True,
            border=True,
        ):
            self._create_section_header(
                self._lbl_spectrum,
                glyph=self._glyphs.headers.spectrum,
            )
            self.spectrum_display = GUISpectrumGraph(
                tag=TAG_INSTRUCTIONS_INSTRUCTION_PANEL_SPECTRUM,
                parent=self.spectrum_tag,
                layout=self._layout,
                language_manager=self._language_manager,
                status_bar=self._status_bar,
            )

    def _create_player_panel(self) -> None:
        self._player_panel.create_panel()

    def close_instruction(self) -> None:
        self.waveform_display.clear_layers()
        self.spectrum_display.clear_layers()
        self.call(self.on_clear_instruction_details)

    def display_instruction(self, instruction_data: Optional[InstructionPanelData]) -> None:
        if instruction_data is None:
            self.close_instruction()
            return

        config = instruction_data.config
        fragment = instruction_data.fragment

        try:
            self.waveform_display.load_library_fragment(fragment)
            self.spectrum_display.load_library_fragment(
                fragment,
                config.sample_rate,
                config.window_size,
            )
        except (KeyError, IndexError, ValueError) as exception:
            logger.error_with_traceback(exception, "Error while plotting library data")
            raise LibraryDisplayError("Could not display library data") from exception

    def set_playback_position(self, position: int) -> None:
        self.waveform_display.set_position(position)
