from pathlib import Path
from typing import Callable, List, Optional, cast

import dearpygui.dearpygui as dpg
import numpy as np

from browser.config.manager import ConfigManager
from browser.graphs.waveform import GUIWaveformDisplay
from browser.panels.panel import GUIPanel
from browser.player.data import AudioData
from browser.player.panel import GUIAudioPlayerPanel
from browser.reconstruction.data import ReconstructionData
from browser.reconstruction.details import GUIReconstructionDetailsPanel
from browser.utils import show_modal_dialog
from constants.browser import (
    DIM_DIALOG_FILE_HEIGHT,
    DIM_DIALOG_FILE_WIDTH,
    DIM_WAVEFORM_DEFAULT_HEIGHT,
    EXT_DIALOG_FTI,
    EXT_DIALOG_WAV,
    LBL_CHECKBOX_NOISE,
    LBL_CHECKBOX_PULSE_1,
    LBL_CHECKBOX_PULSE_2,
    LBL_CHECKBOX_TRIANGLE,
    LBL_RADIO_ORIGINAL_AUDIO,
    LBL_RADIO_RECONSTRUCTION_AUDIO,
    LBL_RECONSTRUCTION_AUDIO_SOURCE,
    LBL_RECONSTRUCTION_EXPORT_WAV,
    LBL_RECONSTRUCTION_WAVEFORM,
    MSG_RECONSTRUCTION_EXPORT_NO_DATA,
    MSG_RECONSTRUCTION_EXPORT_SUCCESS,
    TAG_RECONSTRUCTION_AUDIO_SOURCE_GROUP,
    TAG_RECONSTRUCTION_EXPORT_WAV_BUTTON,
    TAG_RECONSTRUCTION_EXPORT_WAV_STATUS_POPUP,
    TAG_RECONSTRUCTION_GENERATORS_GROUP,
    TAG_RECONSTRUCTION_PANEL,
    TAG_RECONSTRUCTION_PANEL_GROUP,
    TAG_RECONSTRUCTION_PLAYER_PANEL,
    TAG_RECONSTRUCTION_WAVEFORM_DISPLAY,
    TITLE_DIALOG_EXPORT_FTI,
    TITLE_DIALOG_EXPORT_WAV,
    TITLE_DIALOG_RECONSTRUCTION_EXPORT_STATUS,
    TPL_RECONSTRUCTION_AUDIO_SOURCE_RADIO,
    TPL_RECONSTRUCTION_EXPORT_ERROR,
    TPL_RECONSTRUCTION_GENERATOR_CHECKBOX,
    VAL_AUDIO_SOURCE_SELECTOR,
    VAL_DIALOG_FILE_COUNT_SINGLE,
    VAL_PLOT_WIDTH_FULL,
)
from constants.enums import AudioSourceType, FeatureKey, GeneratorName
from utils.audio.device import AudioDeviceManager
from utils.audio.io import write_audio
from utils.fami import write_fti


class GUIReconstructionPanel(GUIPanel):
    def __init__(self, config_manager: ConfigManager, audio_device_manager: AudioDeviceManager) -> None:
        self.config_manager = config_manager
        self.audio_device_manager = audio_device_manager
        self.waveform_display: GUIWaveformDisplay
        self.reconstruction_details: GUIReconstructionDetailsPanel
        self.player_panel: GUIAudioPlayerPanel
        self.reconstruction_data: Optional[ReconstructionData] = None
        self._pending_fti_export: Optional[tuple[GeneratorName, dict]] = None
        self.current_audio_source: AudioSourceType = AudioSourceType.RECONSTRUCTION
        self._export_wav_callback: Optional[Callable[[], None]] = None

        super().__init__(
            tag=TAG_RECONSTRUCTION_PANEL,
            parent_tag=TAG_RECONSTRUCTION_PANEL_GROUP,
        )

    def create_panel(self) -> None:
        self._create_player_panel()
        self._create_audio_source_radio_buttons()
        self._create_export_wav_button()
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

    def _create_audio_source_radio_buttons(self) -> None:
        with dpg.group(horizontal=True, parent=self.parent_tag, tag=TAG_RECONSTRUCTION_AUDIO_SOURCE_GROUP):
            dpg.add_text(LBL_RECONSTRUCTION_AUDIO_SOURCE)
            dpg.add_radio_button(
                items=[LBL_RADIO_RECONSTRUCTION_AUDIO, LBL_RADIO_ORIGINAL_AUDIO],
                tag=TPL_RECONSTRUCTION_AUDIO_SOURCE_RADIO.format(VAL_AUDIO_SOURCE_SELECTOR),
                default_value=LBL_RADIO_RECONSTRUCTION_AUDIO,
                callback=self._on_audio_source_changed,
                horizontal=True,
                enabled=False,
            )

    def _create_export_wav_button(self) -> None:
        dpg.add_button(
            label=LBL_RECONSTRUCTION_EXPORT_WAV,
            tag=TAG_RECONSTRUCTION_EXPORT_WAV_BUTTON,
            parent=self.parent_tag,
            callback=self._handle_export_wav_button_click,
            width=-1,
            enabled=False,
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
        self.reconstruction_details.set_callback(on_instrument_export=self._handle_instrument_export)

    def set_export_wav_callback(self, callback: Callable[[], None]) -> None:
        self._export_wav_callback = callback

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

        self.waveform_display.load_reconstruction_data(self.reconstruction_data, selected_generators)
        self._update_audio_player()

    def _on_generator_checkbox_changed(self) -> None:
        self._update_reconstruction_display()

    def _on_audio_source_changed(self, sender, app_data) -> None:
        if app_data == LBL_RADIO_ORIGINAL_AUDIO:
            self.current_audio_source = AudioSourceType.ORIGINAL
        else:
            self.current_audio_source = AudioSourceType.RECONSTRUCTION
        self._update_audio_player()

    def _update_audio_player(self) -> None:
        if not self.reconstruction_data:
            return

        sample_rate = self.reconstruction_data.reconstruction.config.library.sample_rate

        if self.current_audio_source == AudioSourceType.ORIGINAL:
            audio_data = AudioData.from_array(self.reconstruction_data.original_audio, sample_rate)
        else:
            selected_generators = self._get_selected_generators()
            partial_approximation = self.reconstruction_data.get_partials(selected_generators)
            audio_data = AudioData.from_array(partial_approximation, sample_rate)

        self.player_panel.load_audio_data(audio_data)

    def _update_generator_checkboxes(self, reconstruction_data: ReconstructionData) -> None:
        available_generators = set(reconstruction_data.reconstruction.instructions.keys())

        for generator_name in GeneratorName:
            tag = TPL_RECONSTRUCTION_GENERATOR_CHECKBOX.format(generator_name)
            is_available = generator_name in available_generators

            dpg.configure_item(tag, enabled=is_available, default_value=is_available)
            if is_available:
                dpg.set_value(tag, True)

        radio_tag = TPL_RECONSTRUCTION_AUDIO_SOURCE_RADIO.format(VAL_AUDIO_SOURCE_SELECTOR)
        dpg.configure_item(radio_tag, enabled=True)
        dpg.configure_item(TAG_RECONSTRUCTION_EXPORT_WAV_BUTTON, enabled=True)

    def clear_display(self) -> None:
        self.reconstruction_data = None
        self.current_audio_source = AudioSourceType.RECONSTRUCTION
        self.reconstruction_details.clear_display()
        self.player_panel.clear_audio()
        self.waveform_display.clear_layers()
        self._reset_generator_checkboxes()
        self._reset_audio_source_radio()

    def _reset_generator_checkboxes(self) -> None:
        for generator_name in GeneratorName:
            tag = TPL_RECONSTRUCTION_GENERATOR_CHECKBOX.format(generator_name)
            dpg.configure_item(tag, enabled=False, default_value=False)
            dpg.set_value(tag, False)

    def _reset_audio_source_radio(self) -> None:
        radio_tag = TPL_RECONSTRUCTION_AUDIO_SOURCE_RADIO.format(VAL_AUDIO_SOURCE_SELECTOR)
        dpg.configure_item(radio_tag, enabled=False)
        dpg.set_value(radio_tag, LBL_RADIO_RECONSTRUCTION_AUDIO)
        dpg.configure_item(TAG_RECONSTRUCTION_EXPORT_WAV_BUTTON, enabled=False)

    def _on_player_position_changed(self, position: int) -> None:
        self.waveform_display.set_position(position)

    def _handle_instrument_export(self, generator_name: GeneratorName) -> None:
        if not self.reconstruction_data:
            return

        reconstruction = self.reconstruction_data.reconstruction
        feature_data = reconstruction.export(as_string=False)
        if generator_name not in feature_data:
            return

        generator_features = feature_data[generator_name]
        filename = Path(reconstruction.audio_filepath).stem
        instrument_name = f"{filename} ({generator_name})"

        self._pending_fti_export = (generator_name, generator_features)
        with dpg.file_dialog(
            label=TITLE_DIALOG_EXPORT_FTI,
            width=DIM_DIALOG_FILE_WIDTH,
            height=DIM_DIALOG_FILE_HEIGHT,
            callback=self._handle_fti_export_dialog_result,
            file_count=VAL_DIALOG_FILE_COUNT_SINGLE,
            default_filename=instrument_name,
        ):
            dpg.add_file_extension(EXT_DIALOG_FTI)

    def _handle_fti_export_dialog_result(self, sender, app_data) -> None:
        if not app_data or "filepath_name" not in app_data:
            self._pending_fti_export = None
            return

        filepath = app_data["filepath_name"]
        if not filepath or not self._pending_fti_export:
            self._pending_fti_export = None
            return

        generator_name, generator_features = self._pending_fti_export
        self._pending_fti_export = None

        if not self.reconstruction_data:
            return

        reconstruction = self.reconstruction_data.reconstruction
        filename = Path(reconstruction.audio_filepath).stem
        instrument_name = f"{filename}_{generator_name}"

        write_fti(
            filename=filepath,
            instrument_name=instrument_name,
            volume=cast(Optional[np.ndarray], generator_features.get(FeatureKey.VOLUME)),
            arpeggio=cast(Optional[np.ndarray], generator_features.get(FeatureKey.ARPEGGIO)),
            pitch=cast(Optional[np.ndarray], generator_features.get(FeatureKey.PITCH)),
            hi_pitch=cast(Optional[np.ndarray], generator_features.get(FeatureKey.HI_PITCH)),
            duty_cycle=cast(Optional[np.ndarray], generator_features.get(FeatureKey.DUTY_CYCLE)),
        )

    def _handle_export_wav_button_click(self) -> None:
        if self._export_wav_callback:
            self._export_wav_callback()

    def export_reconstruction_to_wav(self) -> None:
        if not self.reconstruction_data:
            self._show_export_status_dialog(MSG_RECONSTRUCTION_EXPORT_NO_DATA)
            return

        reconstruction = self.reconstruction_data.reconstruction
        filename = Path(reconstruction.audio_filepath).stem

        with dpg.file_dialog(
            label=TITLE_DIALOG_EXPORT_WAV,
            width=DIM_DIALOG_FILE_WIDTH,
            height=DIM_DIALOG_FILE_HEIGHT,
            callback=self._handle_wav_export_dialog_result,
            file_count=VAL_DIALOG_FILE_COUNT_SINGLE,
            default_filename=filename,
        ):
            dpg.add_file_extension(EXT_DIALOG_WAV)

    def _handle_wav_export_dialog_result(self, sender, app_data) -> None:
        if not app_data or "filepath_name" not in app_data:
            return

        filepath = app_data["filepath_name"]
        if not filepath or not self.reconstruction_data:
            return

        selected_generators = self._get_selected_generators()
        partial_approximation = self.reconstruction_data.get_partials(selected_generators)
        sample_rate = self.reconstruction_data.reconstruction.config.library.sample_rate

        try:
            write_audio(filepath, partial_approximation, sample_rate)
            self._show_export_status_dialog(MSG_RECONSTRUCTION_EXPORT_SUCCESS)
        except Exception as error:
            self._show_export_status_dialog(TPL_RECONSTRUCTION_EXPORT_ERROR.format(str(error)))

    def _show_export_status_dialog(self, message: str) -> None:
        def content(parent: str) -> None:
            dpg.add_text(message, parent=parent)

        show_modal_dialog(
            tag=TAG_RECONSTRUCTION_EXPORT_WAV_STATUS_POPUP,
            title=TITLE_DIALOG_RECONSTRUCTION_EXPORT_STATUS,
            content=content,
        )
