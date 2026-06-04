from typing import Callable, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.instructions import InstructionPanelElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.key import TextKey
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.general import (
    SUF_PANEL_CENTER,
    TAG_TAB_GLOBAL_INSTRUCTIONS,
)
from sampletones_application.constants.instructions import (
    SUF_GRAPH_INSTRUCTIONS_INSTRUCTION_WAVEFORM_WINDOW,
    SUF_GRAPH_INSTRUCTIONS_INSTRUCTIONS_SPECTRUM_WINDOW,
    TAG_PANEL_INSTRUCTIONS_INSTRUCTION,
    TAG_PANEL_INSTRUCTIONS_INSTRUCTION_PLAYER,
    TAG_PANEL_INSTRUCTIONS_INSTRUCTION_SPECTRUM,
    TAG_PANEL_INSTRUCTIONS_INSTRUCTION_WAVEFORM,
)
from sampletones_application.layout.graphs import GraphsLayout
from sampletones_application.layout.player import PlayerLayout
from sampletones_application.logic.shared.player import PlayerLogic
from sampletones_application.ui.elements.graphs.spectrum import GUISpectrumGraph
from sampletones_application.ui.elements.graphs.waveform import GUIWaveformGraph
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.panels.player import GUIAudioPlayerPanel
from sampletones_application.utils.dialogs import DialogsRenderer
from sampletones_application.view_model.instruction.data import InstructionPanelData
from sampletones_application.view_model.shared.audio_data import AudioData
from sampletones_core.configs import InstructionsLibraryConfig
from sampletones_shared.exceptions import LibraryDisplayError
from sampletones_shared.logger import logger
from sampletones_shared.types.callback import VoidCallback


class GUIInstructionPanel(GUIPanel):
    def __init__(
        self,
        player_logic: PlayerLogic,
        *,
        layout: GraphsLayout,
        layout_player: PlayerLayout,
        language_manager: LanguageManager,
        dialogs: DialogsRenderer,
    ) -> None:
        self._player_logic = player_logic
        self._layout = layout
        self._layout_player = layout_player
        self._language_manager = language_manager
        self._dialogs = dialogs
        self.player_panel: GUIAudioPlayerPanel
        self.waveform_display: GUIWaveformGraph
        self.spectrum_display: GUISpectrumGraph

        self.on_clear_instruction_details: Optional[VoidCallback] = None
        self.on_instruction_config_changed: Optional[Callable[[Optional[InstructionsLibraryConfig]], None]] = None

        self._lbl_waveform = language_manager[
            TextKey(
                Page.INSTRUCTIONS,
                Panel.INSTRUCTION,
                TextType.LABEL,
                InstructionPanelElements.WAVEFORM_LABEL,
            )
        ]
        self._lbl_spectrum = language_manager[
            TextKey(
                Page.INSTRUCTIONS,
                Panel.INSTRUCTION,
                TextType.LABEL,
                InstructionPanelElements.SPECTRUM_LABEL,
            )
        ]

        self.waveform_tag = f"{TAG_PANEL_INSTRUCTIONS_INSTRUCTION}{SUF_GRAPH_INSTRUCTIONS_INSTRUCTION_WAVEFORM_WINDOW}"
        self.spectrum_tag = f"{TAG_PANEL_INSTRUCTIONS_INSTRUCTION}{SUF_GRAPH_INSTRUCTIONS_INSTRUCTIONS_SPECTRUM_WINDOW}"

        super().__init__(
            tag=TAG_PANEL_INSTRUCTIONS_INSTRUCTION,
            parent=f"{TAG_TAB_GLOBAL_INSTRUCTIONS}{SUF_PANEL_CENTER}",
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
                tag=TAG_PANEL_INSTRUCTIONS_INSTRUCTION_WAVEFORM,
                parent=self.waveform_tag,
                layout=self._layout,
                language_manager=self._language_manager,
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
                tag=TAG_PANEL_INSTRUCTIONS_INSTRUCTION_SPECTRUM,
                parent=self.spectrum_tag,
                layout=self._layout,
                language_manager=self._language_manager,
                label=self._lbl_spectrum,
            )

    def _create_player_panel(self) -> None:
        self.player_panel = GUIAudioPlayerPanel(
            tag=TAG_PANEL_INSTRUCTIONS_INSTRUCTION_PLAYER,
            parent=self.parent,
            player_logic=self._player_logic,
            on_position_changed=self._on_player_position_changed,
            layout=self._layout_player,
            language_manager=self._language_manager,
            dialogs=self._dialogs,
        )

    def close_instruction(self) -> None:
        self.waveform_display.clear_layers()
        self.spectrum_display.clear_layers()
        self.call(self.on_clear_instruction_details)
        self.call(self.on_instruction_config_changed, None)

    def display_instruction(self, instruction_data: Optional[InstructionPanelData]) -> None:
        if instruction_data is None:
            self.close_instruction()
            return

        config = instruction_data.config
        fragment = instruction_data.fragment

        self.call(self.on_instruction_config_changed, config)
        try:
            self.waveform_display.load_library_fragment(fragment)
            self.spectrum_display.load_library_fragment(
                fragment,
                config.sample_rate,
                config.window_size,
            )
        except Exception as exception:
            logger.error_with_traceback(exception, "Error while plotting library data")
            raise LibraryDisplayError("Could not display library data") from exception

        audio_data = AudioData.from_library_fragment(fragment, config.sample_rate)
        self.player_panel.load(audio_data)

    def _on_player_position_changed(self, position: int) -> None:
        self.waveform_display.set_position(position)
