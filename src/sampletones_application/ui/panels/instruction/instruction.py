from typing import Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.instructions import InstructionPanelElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.general import (
    SUF_PANEL_CENTER,
    TAG_GLOBAL_TAB_INSTRUCTIONS,
)
from sampletones_application.constants.instructions import (
    SUF_GRAPH_INSTRUCTIONS_INSTRUCTION_WAVEFORM_WINDOW,
    SUF_GRAPH_INSTRUCTIONS_INSTRUCTIONS_SPECTRUM_WINDOW,
    TAG_INSTRUCTIONS_INSTRUCTION_PANEL,
    TAG_INSTRUCTIONS_INSTRUCTION_PANEL_SPECTRUM,
    TAG_INSTRUCTIONS_INSTRUCTION_PANEL_WAVEFORM,
)
from sampletones_application.layout.graphs import GraphsLayout
from sampletones_application.ui.elements.graphs.spectrum import GUISpectrumGraph
from sampletones_application.ui.elements.graphs.waveform import GUIWaveformGraph
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.panels.player import GUIAudioPlayerPanel
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
        language_manager: LanguageManager,
        status_bar: GUIStatusBar,
    ) -> None:
        self._player_panel = player_panel
        self._layout = layout
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
        self._create_waveform_display()
        self._create_spectrum_display()

    def _create_waveform_display(self) -> None:
        dpg.add_separator()
        with dpg.child_window(
            tag=self.waveform_tag,
            parent=self.parent,
            no_scrollbar=True,
            auto_resize_y=True,
            border=False,
        ):
            self.waveform_display = GUIWaveformGraph(
                tag=TAG_INSTRUCTIONS_INSTRUCTION_PANEL_WAVEFORM,
                parent=self.waveform_tag,
                layout=self._layout,
                language_manager=self._language_manager,
                status_bar=self._status_bar,
                label=self._lbl_waveform,
            )

    def _create_spectrum_display(self) -> None:
        dpg.add_separator()
        with dpg.child_window(
            tag=self.spectrum_tag,
            parent=self.parent,
            no_scrollbar=True,
            auto_resize_y=True,
            border=False,
        ):
            self.spectrum_display = GUISpectrumGraph(
                tag=TAG_INSTRUCTIONS_INSTRUCTION_PANEL_SPECTRUM,
                parent=self.spectrum_tag,
                layout=self._layout,
                language_manager=self._language_manager,
                status_bar=self._status_bar,
                label=self._lbl_spectrum,
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
