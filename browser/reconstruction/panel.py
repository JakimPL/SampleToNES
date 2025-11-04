from typing import List, Optional

import dearpygui.dearpygui as dpg

from browser.config.manager import ConfigManager
from browser.graphs.waveform import GUIWaveformDisplay
from browser.panels.panel import GUIPanel
from browser.player.data import AudioData
from browser.player.panel import GUIAudioPlayerPanel
from browser.reconstruction.data import ReconstructionData
from browser.reconstruction.details import GUIReconstructionDetailsPanel
from constants.browser import (
    DIM_WAVEFORM_DEFAULT_HEIGHT,
    LBL_CHECKBOX_NOISE,
    LBL_CHECKBOX_PULSE_1,
    LBL_CHECKBOX_PULSE_2,
    LBL_CHECKBOX_TRIANGLE,
    LBL_RECONSTRUCTION_WAVEFORM,
    TAG_RECONSTRUCTION_GENERATORS_GROUP,
    TAG_RECONSTRUCTION_PANEL,
    TAG_RECONSTRUCTION_PANEL_GROUP,
    TAG_RECONSTRUCTION_PLAYER_PANEL,
    TAG_RECONSTRUCTION_WAVEFORM_DISPLAY,
    TPL_RECONSTRUCTION_GENERATOR_CHECKBOX,
    VAL_PLOT_WIDTH_FULL,
)
from constants.enums import GeneratorName
from utils.audio.device import AudioDeviceManager


class GUIReconstructionPanel(GUIPanel):
    def __init__(self, config_manager: ConfigManager, audio_device_manager: AudioDeviceManager) -> None:
        self.config_manager = config_manager
        self.audio_device_manager = audio_device_manager
        self.waveform_display: GUIWaveformDisplay
        self.reconstruction_details: GUIReconstructionDetailsPanel
        self.player_panel: GUIAudioPlayerPanel
        self.reconstruction_data: Optional[ReconstructionData] = None

        super().__init__(
            tag=TAG_RECONSTRUCTION_PANEL,
            parent_tag=TAG_RECONSTRUCTION_PANEL_GROUP,
        )

    def create_panel(self) -> None:
        self._create_player_panel()
        dpg.add_separator(parent=self.parent_tag)
        self._create_waveform_display()
        self._create_generator_checkboxes()
        dpg.add_separator(parent=self.parent_tag)
        self._create_reconstruction_details()

    def _create_player_panel(self) -> None:
        self.player_panel = GUIAudioPlayerPanel(
            tag=TAG_RECONSTRUCTION_PLAYER_PANEL,
            parent=self.parent_tag,
            on_position_changed=self._on_player_position_changed,
            audio_device_manager=self.audio_device_manager,
        )

    def _create_waveform_display(self) -> None:
        self.waveform_display = GUIWaveformDisplay(
            tag=TAG_RECONSTRUCTION_WAVEFORM_DISPLAY,
            width=VAL_PLOT_WIDTH_FULL,
            height=DIM_WAVEFORM_DEFAULT_HEIGHT,
            parent=self.parent_tag,
            label=LBL_RECONSTRUCTION_WAVEFORM,
        )

    def _create_generator_checkboxes(self) -> None:
        generator_labels = {
            GeneratorName.PULSE1: LBL_CHECKBOX_PULSE_1,
            GeneratorName.PULSE2: LBL_CHECKBOX_PULSE_2,
            GeneratorName.TRIANGLE: LBL_CHECKBOX_TRIANGLE,
            GeneratorName.NOISE: LBL_CHECKBOX_NOISE,
        }

        with dpg.group(horizontal=True, parent=self.parent_tag, tag=TAG_RECONSTRUCTION_GENERATORS_GROUP):
            for generator_name, label in generator_labels.items():
                tag = TPL_RECONSTRUCTION_GENERATOR_CHECKBOX.format(generator_name)
                dpg.add_checkbox(
                    label=label,
                    tag=tag,
                    default_value=False,
                    enabled=False,
                    callback=self._on_generator_checkbox_changed,
                )

    def _create_reconstruction_details(self) -> None:
        self.reconstruction_details = GUIReconstructionDetailsPanel()
        self.reconstruction_details.create_panel()

    def display_reconstruction(self, reconstruction_data: ReconstructionData) -> None:
        self.reconstruction_data = reconstruction_data
        self.config_manager.load_config(reconstruction_data.config)

        self.reconstruction_details.display_reconstruction(reconstruction_data.reconstruction)

        self._update_generator_checkboxes(reconstruction_data)
        self._update_reconstruction_display()

    def _get_selected_generators(self) -> List[GeneratorName]:
        selected_generators = []
        for generator_name in GeneratorName:
            tag = TPL_RECONSTRUCTION_GENERATOR_CHECKBOX.format(generator_name)
            if dpg.get_value(tag):
                selected_generators.append(generator_name)
        return selected_generators

    def _update_reconstruction_display(self) -> None:
        if not self.reconstruction_data:
            return

        selected_generators = self._get_selected_generators()
        sample_rate = self.reconstruction_data.reconstruction.config.library.sample_rate

        self.waveform_display.load_reconstruction_data(self.reconstruction_data, selected_generators)

        partial_approximation = self.reconstruction_data.get_partials(selected_generators)
        audio_data = AudioData.from_array(partial_approximation, sample_rate)
        self.player_panel.load_audio_data(audio_data)

    def _on_generator_checkbox_changed(self) -> None:
        self._update_reconstruction_display()

    def _update_generator_checkboxes(self, reconstruction_data: ReconstructionData) -> None:
        available_generators = set(reconstruction_data.reconstruction.instructions.keys())

        for generator_name in GeneratorName:
            tag = TPL_RECONSTRUCTION_GENERATOR_CHECKBOX.format(generator_name)
            is_available = generator_name in available_generators

            dpg.configure_item(tag, enabled=is_available, default_value=is_available)
            if is_available:
                dpg.set_value(tag, True)

    def clear_display(self) -> None:
        self.reconstruction_data = None
        self.reconstruction_details.clear_display()
        self.player_panel.clear_audio()
        self.waveform_display.clear_layers()
        self._reset_generator_checkboxes()

    def _reset_generator_checkboxes(self) -> None:
        for generator_name in GeneratorName:
            tag = TPL_RECONSTRUCTION_GENERATOR_CHECKBOX.format(generator_name)
            dpg.configure_item(tag, enabled=False, default_value=False)
            dpg.set_value(tag, False)

    def _on_player_position_changed(self, position: int) -> None:
        self.waveform_display.set_position(position)
