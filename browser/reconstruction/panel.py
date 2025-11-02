from typing import Optional

import dearpygui.dearpygui as dpg
import numpy as np

from browser.graphs.layers.array import ArrayLayer
from browser.graphs.layers.waveform import WaveformLayer
from browser.graphs.waveform import GUIWaveformDisplay
from browser.panel import GUIPanel
from browser.player.data import AudioData
from browser.player.panel import GUIAudioPlayerPanel
from browser.reconstruction.details import GUIReconstructionDetailsPanel
from browser.reconstruction.export import GUIReconstructionExportPanel
from constants.browser import (
    CLR_WAVEFORM_LAYER_RECONSTRUCTION,
    CLR_WAVEFORM_LAYER_SAMPLE,
    DIM_WAVEFORM_DEFAULT_HEIGHT,
    LBL_PLOT_ORIGINAL,
    LBL_PLOT_RECONSTRUCTION,
    LBL_RECONSTRUCTION_WAVEFORM,
    TAG_RECONSTRUCTION_PANEL,
    TAG_RECONSTRUCTION_PANEL_GROUP,
    TAG_RECONSTRUCTION_PLAYER_PANEL,
    TAG_RECONSTRUCTION_WAVEFORM_DISPLAY,
    VAL_PLOT_WIDTH_FULL,
    VAL_WAVEFORM_RECONSTRUCTION_THICKNESS,
    VAL_WAVEFORM_SAMPLE_THICKNESS,
)
from reconstructor.reconstruction import Reconstruction
from utils.audio.device import AudioDeviceManager


class GUIReconstructionPanel(GUIPanel):
    def __init__(self, audio_device_manager: AudioDeviceManager) -> None:
        self.audio_device_manager = audio_device_manager
        self.waveform_display: GUIWaveformDisplay
        self.reconstruction_details: GUIReconstructionDetailsPanel
        self.reconstruction_export: GUIReconstructionExportPanel
        self.player_panel: GUIAudioPlayerPanel
        self.current_reconstruction: Optional[Reconstruction] = None
        self.original_audio: Optional[np.ndarray] = None

        super().__init__(
            tag=TAG_RECONSTRUCTION_PANEL,
            parent_tag=TAG_RECONSTRUCTION_PANEL_GROUP,
        )

    def create_panel(self) -> None:
        self._create_player_panel()
        dpg.add_separator(parent=self.parent_tag)
        self._create_waveform_display()
        dpg.add_separator(parent=self.parent_tag)
        self._create_reconstruction_details()
        dpg.add_separator(parent=self.parent_tag)
        self._create_reconstruction_export()

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

    def _create_reconstruction_details(self) -> None:
        self.reconstruction_details = GUIReconstructionDetailsPanel()
        self.reconstruction_details.create_panel()

    def _create_reconstruction_export(self) -> None:
        self.reconstruction_export = GUIReconstructionExportPanel()
        self.reconstruction_export.create_panel()

    def display_reconstruction(self, reconstruction: Reconstruction, original_audio: np.ndarray) -> None:
        self.current_reconstruction = reconstruction
        self.original_audio = original_audio

        self.reconstruction_details.display_reconstruction(reconstruction)
        self.reconstruction_export.load_reconstruction(reconstruction)

        sample_rate = reconstruction.config.library.sample_rate
        self._load_waveform_data(reconstruction, original_audio)
        self._load_audio_data(reconstruction, sample_rate)

    def _load_waveform_data(self, reconstruction: Reconstruction, original_audio: np.ndarray) -> None:
        self.waveform_display.clear_layers()

        self.waveform_display.add_layer(
            ArrayLayer(
                data=original_audio,
                name=LBL_PLOT_ORIGINAL,
                color=CLR_WAVEFORM_LAYER_SAMPLE,
                line_thickness=VAL_WAVEFORM_SAMPLE_THICKNESS,
            )
        )

        self.waveform_display.add_layer(
            ArrayLayer(
                data=reconstruction.approximation,
                name=LBL_PLOT_RECONSTRUCTION,
                color=CLR_WAVEFORM_LAYER_RECONSTRUCTION,
                line_thickness=VAL_WAVEFORM_RECONSTRUCTION_THICKNESS,
            )
        )

        self.waveform_display.x_min = 0.0
        self.waveform_display.x_max = float(len(original_audio))
        self.waveform_display._update_axes_limits()

    def _load_audio_data(self, reconstruction: Reconstruction, sample_rate: int) -> None:
        audio_data = AudioData.from_array(reconstruction.approximation, sample_rate)
        self.player_panel.load_audio_data(audio_data)

    def clear_display(self) -> None:
        self.current_reconstruction = None
        self.original_audio = None
        self.reconstruction_details.clear_display()
        self.reconstruction_export.clear()
        self.player_panel.clear_audio()
        self.waveform_display.clear_layers()

    def _on_player_position_changed(self, position: int) -> None:
        pass
