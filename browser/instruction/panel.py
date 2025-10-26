from typing import Optional

import dearpygui.dearpygui as dpg
from pydantic import BaseModel

from browser.constants import (
    LABEL_INSTRUCTION_WAVEFORM,
    MSG_INSTRUCTION_DETAILS,
    MSG_NO_INSTRUCTION_SELECTED,
    PLOT_WIDTH_FULL,
    WAVEFORM_DEFAULT_HEIGHT,
)
from browser.player.data import AudioData
from browser.player.panel import AudioPlayerPanel
from browser.waveform.waveform import Waveform
from constants import SAMPLE_RATE
from library.data import LibraryFragment
from typehints.instructions import InstructionUnion


class InstructionPanelData(BaseModel, frozen=True):
    generator_class_name: str
    instruction: InstructionUnion
    fragment: Optional[LibraryFragment] = None


class InstructionPanelLogic:
    def __init__(self) -> None:
        self.current_data: Optional[InstructionPanelData] = None

    def set_instruction_data(
        self, generator_class_name: str, instruction: InstructionUnion, fragment: Optional[LibraryFragment] = None
    ) -> InstructionPanelData:
        self.current_data = InstructionPanelData(
            generator_class_name=generator_class_name, instruction=instruction, fragment=fragment
        )
        return self.current_data

    def clear_data(self) -> None:
        self.current_data = None

    def create_audio_data(self, fragment: LibraryFragment) -> AudioData:
        return AudioData.from_library_fragment(fragment, SAMPLE_RATE)

    def get_display_text(self) -> str:
        if self.current_data:
            return f"Generator: {self.current_data.generator_class_name}\nInstruction: {self.current_data.instruction.name}"
        return MSG_NO_INSTRUCTION_SELECTED


class InstructionPanelGUI:
    def __init__(self, parent_tag: str) -> None:
        self.parent_tag = parent_tag
        self.logic = InstructionPanelLogic()
        self.player_panel: AudioPlayerPanel
        self.waveform_display: Waveform

    def create_panel(self) -> None:
        dpg.add_text(MSG_INSTRUCTION_DETAILS, parent=self.parent_tag)
        dpg.add_separator(parent=self.parent_tag)

        dpg.add_text(MSG_NO_INSTRUCTION_SELECTED, tag=f"{self.parent_tag}_instruction_info", parent=self.parent_tag)

        dpg.add_separator(parent=self.parent_tag)

        self._create_player_panel()
        self._create_waveform_display()

    def _create_player_panel(self) -> None:
        player_tag = f"{self.parent_tag}_player"
        self.player_panel = AudioPlayerPanel(
            tag=player_tag, parent=self.parent_tag, on_position_changed=self._on_player_position_changed
        )

    def _create_waveform_display(self) -> None:
        waveform_tag = f"{self.parent_tag}_waveform"
        self.waveform_display = Waveform(
            tag=waveform_tag,
            width=PLOT_WIDTH_FULL,
            height=WAVEFORM_DEFAULT_HEIGHT,
            parent=self.parent_tag,
            label=LABEL_INSTRUCTION_WAVEFORM,
        )

    def display_instruction(
        self, generator_class_name: str, instruction: InstructionUnion, fragment: Optional[LibraryFragment] = None
    ) -> None:
        self.logic.set_instruction_data(generator_class_name, instruction, fragment)
        self._update_display()

    def clear_display(self) -> None:
        self.logic.clear_data()
        self._update_display()

    def _update_display(self) -> None:
        display_text = self.logic.get_display_text()
        dpg.set_value(f"{self.parent_tag}_instruction_info", display_text)

        if self.logic.current_data and self.logic.current_data.fragment:
            self.waveform_display.load_library_fragment(self.logic.current_data.fragment)
            audio_data = self.logic.create_audio_data(self.logic.current_data.fragment)
            self.player_panel.load_audio_data(audio_data)
        else:
            self.waveform_display.clear_layers()
            self.player_panel.clear_audio()

    def _on_player_position_changed(self, position: int) -> None:
        pass
