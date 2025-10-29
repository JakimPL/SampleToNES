from typing import Optional

import dearpygui.dearpygui as dpg

from browser.constants import (
    DIM_WAVEFORM_DEFAULT_HEIGHT,
    LBL_INSTRUCTION_SPECTRUM,
    LBL_INSTRUCTION_WAVEFORM,
    TAG_INSTRUCTION_PANEL,
    TAG_INSTRUCTION_PANEL_GROUP,
    TAG_INSTRUCTION_SPECTRUM_DISPLAY,
    TAG_INSTRUCTION_WAVEFORM_DISPLAY,
    VAL_PLOT_WIDTH_FULL,
)
from browser.graphs.spectrum import SpectrumDisplay
from browser.graphs.waveform import WaveformDisplay
from browser.instruction.details import GUIInstructionDetailsPanel
from browser.panels.panel import GUIPanel
from browser.player.data import AudioData
from browser.player.panel import AudioPlayerPanel
from configs.library import LibraryConfig
from constants import SAMPLE_RATE
from library.data import LibraryFragment
from typehints.instructions import InstructionUnion
from utils.audio.device import AudioDeviceManager


class GUIInstructionPanel(GUIPanel):
    def __init__(self, audio_device_manager: AudioDeviceManager) -> None:
        super().__init__(
            tag=TAG_INSTRUCTION_PANEL,
            parent_tag=TAG_INSTRUCTION_PANEL_GROUP,
        )

        self.audio_device_manager = audio_device_manager
        self.waveform_display: WaveformDisplay
        self.spectrum_display: SpectrumDisplay
        self.instruction_details: GUIInstructionDetailsPanel
        self.player_panel: AudioPlayerPanel
        self.library_config: Optional[LibraryConfig] = None

    def create_panel(self) -> None:
        self._create_player_panel()
        dpg.add_separator(parent=self.parent_tag)
        self._create_waveform_display()
        dpg.add_separator(parent=self.parent_tag)
        self._create_spectrum_display()
        dpg.add_separator(parent=self.parent_tag)
        self._create_instruction_details()

    def _create_waveform_display(self) -> None:
        self.waveform_display = WaveformDisplay(
            tag=TAG_INSTRUCTION_WAVEFORM_DISPLAY,
            width=VAL_PLOT_WIDTH_FULL,
            height=DIM_WAVEFORM_DEFAULT_HEIGHT,
            parent=self.parent_tag,
            label=LBL_INSTRUCTION_WAVEFORM,
        )

    def _create_spectrum_display(self) -> None:
        self.spectrum_display = SpectrumDisplay(
            tag=TAG_INSTRUCTION_SPECTRUM_DISPLAY,
            width=VAL_PLOT_WIDTH_FULL,
            height=DIM_WAVEFORM_DEFAULT_HEIGHT,
            parent=self.parent_tag,
            label=LBL_INSTRUCTION_SPECTRUM,
        )

    def _create_instruction_details(self) -> None:
        self.instruction_details = GUIInstructionDetailsPanel()
        self.instruction_details.create_panel()

    def _create_player_panel(self) -> None:
        player_tag = f"{self.parent_tag}_player"
        self.player_panel = AudioPlayerPanel(
            tag=player_tag,
            parent=self.parent_tag,
            on_position_changed=self._on_player_position_changed,
            audio_device_manager=self.audio_device_manager,
        )

    def display_instruction(
        self,
        generator_class_name: str,
        instruction: InstructionUnion,
        fragment: LibraryFragment,
        library_config: LibraryConfig,
    ) -> None:
        self.library_config = library_config
        self.instruction_details.display_instruction(generator_class_name, instruction, fragment)

        if fragment:
            sample_rate = library_config.sample_rate
            frame_length = library_config.window_size
            self.waveform_display.load_library_fragment(fragment)
            self.spectrum_display.load_library_fragment(fragment, sample_rate, frame_length)
            audio_data = AudioData.from_library_fragment(fragment, sample_rate)
            self.player_panel.load_audio_data(audio_data)
        else:
            self._clear_displays()

    def clear_display(self) -> None:
        self.instruction_details.clear_display()
        self._clear_displays()

    def _clear_displays(self) -> None:
        if dpg.does_item_exist(self.waveform_display.y_axis_tag):
            self.waveform_display.clear_layers()
        if dpg.does_item_exist(self.spectrum_display.y_axis_tag):
            pass
            # self.spectrum_display.clear_layers()
        if hasattr(self, "player_panel"):
            self.player_panel.clear_audio()

    def _on_player_position_changed(self, position: int) -> None:
        pass
