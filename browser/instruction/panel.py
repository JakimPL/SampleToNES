from typing import Optional

import dearpygui.dearpygui as dpg

from browser.constants import (
    DIM_WAVEFORM_DEFAULT_HEIGHT,
    LBL_INSTRUCTION_WAVEFORM,
    VAL_PLOT_WIDTH_FULL,
)
from browser.instruction.details import InstructionDetailsPanel
from browser.player.data import AudioData
from browser.player.panel import AudioPlayerPanel
from browser.waveform.waveform import Waveform
from constants import SAMPLE_RATE
from library.data import LibraryFragment
from typehints.instructions import InstructionUnion
from utils.audio.device import AudioDeviceManager


class InstructionPanelGUI:
    def __init__(self, parent_tag: str, audio_device_manager: AudioDeviceManager) -> None:
        self.parent_tag = parent_tag
        self.audio_device_manager = audio_device_manager
        self.waveform_display: Waveform
        self.instruction_details: InstructionDetailsPanel
        self.player_panel: AudioPlayerPanel

    def create_panel(self) -> None:
        self._create_player_panel()
        dpg.add_separator(parent=self.parent_tag)
        self._create_waveform_display()
        dpg.add_separator(parent=self.parent_tag)
        self._create_instruction_details()

    def _create_waveform_display(self) -> None:
        waveform_tag = f"{self.parent_tag}_waveform"
        self.waveform_display = Waveform(
            tag=waveform_tag,
            width=VAL_PLOT_WIDTH_FULL,
            height=DIM_WAVEFORM_DEFAULT_HEIGHT,
            parent=self.parent_tag,
            label=LBL_INSTRUCTION_WAVEFORM,
        )

    def _create_instruction_details(self) -> None:
        details_tag = f"{self.parent_tag}_details"
        self.instruction_details = InstructionDetailsPanel(details_tag)
        self.instruction_details.create_panel(self.parent_tag)

    def _create_player_panel(self) -> None:
        player_tag = f"{self.parent_tag}_player"
        self.player_panel = AudioPlayerPanel(
            tag=player_tag,
            parent=self.parent_tag,
            on_position_changed=self._on_player_position_changed,
            audio_device_manager=self.audio_device_manager,
        )

    def display_instruction(
        self, generator_class_name: str, instruction: InstructionUnion, fragment: Optional[LibraryFragment] = None
    ) -> None:
        self.instruction_details.display_instruction(generator_class_name, instruction, fragment)

        if fragment:
            self.waveform_display.load_library_fragment(fragment)
            audio_data = AudioData.from_library_fragment(fragment, SAMPLE_RATE)
            self.player_panel.load_audio_data(audio_data)
        else:
            self._clear_displays()

    def clear_display(self) -> None:
        self.instruction_details.clear_display()
        self._clear_displays()

    def _clear_displays(self) -> None:
        if hasattr(self, "waveform_display") and dpg.does_item_exist(self.waveform_display.y_axis_tag):
            self.waveform_display.clear_layers()
        if hasattr(self, "player_panel"):
            self.player_panel.clear_audio()

    def _on_player_position_changed(self, position: int) -> None:
        pass
