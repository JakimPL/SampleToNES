from pathlib import Path
from typing import Callable, List, Optional

import dearpygui.dearpygui as dpg

from sampletones.audio import AudioDeviceManager, write_wave
from sampletones.constants.enums import AudioSourceType, GeneratorName
from sampletones.constants.paths import EXT_FILE_INSTRUMENT, EXT_FILE_WAVE
from sampletones.reconstruction import Reconstruction
from sampletones.typehints import Sender
from sampletones.utils import to_path
from sampletones.utils.logger import logger

from ...config.application.manager import ApplicationConfigManager
from ...config.manager import ConfigManager
from ...constants import (
    DIM_DIALOG_HEIGHT_FILE,
    DIM_DIALOG_WIDTH_FILE,
    DIM_WAVEFORM_HEIGHT,
    LBL_BUTTON_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_WAV,
    LBL_CHECKBOX_NOISE,
    LBL_CHECKBOX_PULSE_1,
    LBL_CHECKBOX_PULSE_2,
    LBL_CHECKBOX_TRIANGLE,
    LBL_PLOT_LABEL_RECONSTRUCTIONS_RECONSTRUCION_WAVEFORM,
    LBL_RADIO_RECONSTRUCTIONS_RECONSTRUCTION_AUDIO,
    LBL_RADIO_RECONSTRUCTIONS_RECONSTRUCTION_ORIGINAL_AUDIO,
    LBL_TEXT_RECONSTRUCTIONS_RECONSTRUCTION_AUDIO_SOURCE,
    MSG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_FTI_FAILED,
    MSG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_FTI_SUCCESS,
    MSG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_FTIS_FAILED,
    MSG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_FTIS_SUCCESS,
    MSG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_WAV_FAILED,
    MSG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_WAV_SUCCESS,
    SUF_PANEL_CENTER,
    SUF_RECONSTRUCTIONS_RECONSTRUCTION_AUDIO,
    SUF_RECONSTRUCTIONS_RECONSTRUCTION_PLOT,
    TAG_BUTTON_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_WAV,
    TAG_GROUP_RECONSTRUCTIONS_RECONSTRUCTION_AUDIO_SOURCE,
    TAG_GROUP_RECONSTRUCTIONS_RECONSTRUCTION_GENERATORS,
    TAG_PANEL_RECONSTRUCTIONS_RECONSTRUCTION,
    TAG_PANEL_RECONSTRUCTIONS_RECONSTRUCTION_PLAYER,
    TAG_PANEL_RECONSTRUCTIONS_RECONSTRUCTION_WAVEFORM,
    TAG_TAB_RECONSTRUCTIONS,
    TPL_TAG_CHECKBOX_RECONSTRUCTIONS_RECONSTRUCTION_GENERATOR,
    TPL_TAG_RADIO_RECONSTRUCTIONS_RECONSTRUCTION_AUDIO_SOURCE,
    TTL_DIALOG_EXPORT_FTI,
    TTL_DIALOG_EXPORT_WAV,
    TTL_DIALOG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_STATUS,
    VAL_DIALOG_GLOBAL_FILE_COUNT_SINGLE,
    VAL_PLOT_WIDTH_GLOBAL_FULL,
    VAL_RADIO_RECONSTRUCTIONS_RECONSTRUCTION_AUDIO_SOURCE,
)
from ...elements.button import GUIButton
from ...elements.fonts.font import Font
from ...elements.fonts.registry import FontRegistry
from ...elements.graphs.waveform import GUIWaveformDisplay
from ...elements.panel import GUIPanel
from ...player.data import AudioData
from ...reconstruction.data import ReconstructionData
from ...utils.dialogs import show_error_dialog, show_message_with_path_dialog
from ...utils.dpg import dpg_configure_item, dpg_set_value
from ...utils.file import file_dialog_handler
from ..player import GUIAudioPlayerPanel


class GUIReconstructionPanel(GUIPanel):
    def __init__(
        self,
        config_manager: ConfigManager,
        application_config_manager: ApplicationConfigManager,
        audio_device_manager: AudioDeviceManager,
    ) -> None:
        self.config_manager = config_manager
        self.application_config_manager = application_config_manager
        self.audio_device_manager = audio_device_manager
        self.waveform_display: GUIWaveformDisplay
        self.player_panel: GUIAudioPlayerPanel

        self.reconstruction_data: Optional[ReconstructionData] = None
        self.current_audio_source: AudioSourceType = AudioSourceType.RECONSTRUCTION
        self._pending_generator_name: Optional[GeneratorName] = None

        self._on_export_wav: Optional[Callable[[], None]] = None
        self._on_display_reconstruction_details: Optional[Callable[[Reconstruction], None]] = None
        self._on_clear_reconstruction_details: Optional[Callable[[], None]] = None
        self._on_change_audio_state: Optional[Callable[[], None]] = None

        self.audio_tag = f"{TAG_PANEL_RECONSTRUCTIONS_RECONSTRUCTION}{SUF_RECONSTRUCTIONS_RECONSTRUCTION_AUDIO}"
        self.plot_tag = f"{TAG_PANEL_RECONSTRUCTIONS_RECONSTRUCTION}{SUF_RECONSTRUCTIONS_RECONSTRUCTION_PLOT}"

        super().__init__(
            tag=TAG_PANEL_RECONSTRUCTIONS_RECONSTRUCTION,
            parent=f"{TAG_TAB_RECONSTRUCTIONS}{SUF_PANEL_CENTER}",
        )

    def create_panel(self) -> None:
        self._create_player_panel()
        self._create_audio_panel()
        self._create_plot_panel()

    def is_loaded(self) -> bool:
        return self.reconstruction_data is not None

    def display_reconstruction(self, reconstruction_data: ReconstructionData) -> None:
        self.reconstruction_data = reconstruction_data
        self.config_manager.load_config(reconstruction_data.config)

        if self._on_display_reconstruction_details:
            self._on_display_reconstruction_details(reconstruction_data.reconstruction)

        self._update_generator_checkboxes(reconstruction_data)
        self._update_reconstruction_display()

    def close_reconstruction(self) -> None:
        self._clear_display()

    def _create_audio_panel(self) -> None:
        dpg.add_separator()
        with dpg.child_window(
            tag=self.audio_tag,
            parent=self.parent,
            no_scrollbar=True,
            auto_resize_y=True,
            border=False,
        ):
            self._create_audio_source_radio_buttons()
            self._create_export_wav_button()

    def _create_plot_panel(self) -> None:
        dpg.add_separator()
        with dpg.child_window(
            tag=self.plot_tag,
            parent=self.parent,
            no_scrollbar=True,
            auto_resize_y=True,
            border=False,
        ):
            self._create_waveform_display()
            self._create_generator_checkboxes()

    def _create_player_panel(self) -> None:
        self.player_panel = GUIAudioPlayerPanel(
            tag=TAG_PANEL_RECONSTRUCTIONS_RECONSTRUCTION_PLAYER,
            parent=self.parent,
            audio_device_manager=self.audio_device_manager,
            on_position_changed=self._on_player_position_changed,
            on_change_audio_state=self._on_change_audio_state,
        )

    def _create_audio_source_radio_buttons(self) -> None:
        dpg.add_text(LBL_TEXT_RECONSTRUCTIONS_RECONSTRUCTION_AUDIO_SOURCE)
        with dpg.group(
            horizontal=True, parent=self.audio_tag, tag=TAG_GROUP_RECONSTRUCTIONS_RECONSTRUCTION_AUDIO_SOURCE
        ):
            radio_button_tag = TPL_TAG_RADIO_RECONSTRUCTIONS_RECONSTRUCTION_AUDIO_SOURCE.format(
                VAL_RADIO_RECONSTRUCTIONS_RECONSTRUCTION_AUDIO_SOURCE
            )
            dpg.add_radio_button(
                items=[
                    LBL_RADIO_RECONSTRUCTIONS_RECONSTRUCTION_AUDIO,
                    LBL_RADIO_RECONSTRUCTIONS_RECONSTRUCTION_ORIGINAL_AUDIO,
                ],
                tag=radio_button_tag,
                default_value=LBL_RADIO_RECONSTRUCTIONS_RECONSTRUCTION_AUDIO,
                callback=self._on_audio_source_changed,
                horizontal=True,
                enabled=False,
            )
            FontRegistry.bind_to_item(radio_button_tag, Font.REGULAR_SMALL)

    def _create_export_wav_button(self) -> None:
        GUIButton(
            label=LBL_BUTTON_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_WAV,
            tag=TAG_BUTTON_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_WAV,
            parent=self.audio_tag,
            callback=self._handle_export_wav_button_click,
            width=-1,
            enabled=False,
        )

    def _create_waveform_display(self) -> None:
        self.waveform_display = GUIWaveformDisplay(
            tag=TAG_PANEL_RECONSTRUCTIONS_RECONSTRUCTION_WAVEFORM,
            width=VAL_PLOT_WIDTH_GLOBAL_FULL,
            height=DIM_WAVEFORM_HEIGHT,
            parent=self.plot_tag,
            label=LBL_PLOT_LABEL_RECONSTRUCTIONS_RECONSTRUCION_WAVEFORM,
        )

    def _create_generator_checkboxes(self) -> None:
        generator_labels = {
            GeneratorName.PULSE1: LBL_CHECKBOX_PULSE_1,
            GeneratorName.PULSE2: LBL_CHECKBOX_PULSE_2,
            GeneratorName.TRIANGLE: LBL_CHECKBOX_TRIANGLE,
            GeneratorName.NOISE: LBL_CHECKBOX_NOISE,
        }

        with dpg.group(horizontal=True, parent=self.plot_tag, tag=TAG_GROUP_RECONSTRUCTIONS_RECONSTRUCTION_GENERATORS):
            for generator_name, label in generator_labels.items():
                tag = TPL_TAG_CHECKBOX_RECONSTRUCTIONS_RECONSTRUCTION_GENERATOR.format(generator_name)
                dpg.add_checkbox(
                    label=label,
                    tag=tag,
                    default_value=False,
                    enabled=False,
                    callback=self._on_generator_checkbox_changed,
                )

    def set_callbacks(
        self,
        on_export_wav: Optional[Callable[[], None]] = None,
        on_display_reconstruction_details: Optional[Callable[[Reconstruction], None]] = None,
        on_clear_reconstruction_details: Optional[Callable[[], None]] = None,
        on_change_audio_state: Optional[Callable[[], None]] = None,
    ) -> None:
        if on_export_wav is not None:
            self._on_export_wav = on_export_wav
        if on_display_reconstruction_details is not None:
            self._on_display_reconstruction_details = on_display_reconstruction_details
        if on_clear_reconstruction_details is not None:
            self._on_clear_reconstruction_details = on_clear_reconstruction_details
        if on_change_audio_state is not None:
            self._on_change_audio_state = on_change_audio_state

    def _get_selected_generators(self) -> List[GeneratorName]:
        selected_generators = []
        for generator_name in GeneratorName:
            tag = TPL_TAG_CHECKBOX_RECONSTRUCTIONS_RECONSTRUCTION_GENERATOR.format(generator_name)
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

    def _on_audio_source_changed(self, sender: Sender, app_data: str) -> None:
        if app_data == LBL_RADIO_RECONSTRUCTIONS_RECONSTRUCTION_ORIGINAL_AUDIO:
            self.current_audio_source = AudioSourceType.ORIGINAL
        else:
            self.current_audio_source = AudioSourceType.RECONSTRUCTION
        self._update_audio_player()

    def _update_audio_player(self) -> None:
        if not self.reconstruction_data:
            return

        sample_rate = self.reconstruction_data.reconstruction.config.sample_rate

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
            tag = TPL_TAG_CHECKBOX_RECONSTRUCTIONS_RECONSTRUCTION_GENERATOR.format(generator_name)
            is_available = generator_name in available_generators

            dpg_configure_item(tag, enabled=is_available, default_value=is_available)
            if is_available:
                dpg_set_value(tag, True)

        radio_tag = TPL_TAG_RADIO_RECONSTRUCTIONS_RECONSTRUCTION_AUDIO_SOURCE.format(
            VAL_RADIO_RECONSTRUCTIONS_RECONSTRUCTION_AUDIO_SOURCE
        )
        dpg_configure_item(radio_tag, enabled=True)
        dpg_configure_item(TAG_BUTTON_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_WAV, enabled=True)

    def _clear_display(self) -> None:
        self.reconstruction_data = None
        self.current_audio_source = AudioSourceType.RECONSTRUCTION

        if self._on_clear_reconstruction_details:
            self._on_clear_reconstruction_details()

        self.player_panel.clear_audio()
        self.waveform_display.clear_layers()
        self._reset_generator_checkboxes()
        self._reset_audio_source_radio()

    def _reset_generator_checkboxes(self) -> None:
        for generator_name in GeneratorName:
            tag = TPL_TAG_CHECKBOX_RECONSTRUCTIONS_RECONSTRUCTION_GENERATOR.format(generator_name)
            dpg_configure_item(tag, enabled=False, default_value=False)
            dpg_set_value(tag, False)

    def _reset_audio_source_radio(self) -> None:
        radio_tag = TPL_TAG_RADIO_RECONSTRUCTIONS_RECONSTRUCTION_AUDIO_SOURCE.format(
            VAL_RADIO_RECONSTRUCTIONS_RECONSTRUCTION_AUDIO_SOURCE
        )
        dpg_configure_item(radio_tag, enabled=False)
        dpg_set_value(radio_tag, LBL_RADIO_RECONSTRUCTIONS_RECONSTRUCTION_AUDIO)
        dpg_configure_item(TAG_BUTTON_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_WAV, enabled=False)

    def _on_player_position_changed(self, position: int) -> None:
        self.waveform_display.set_position(position)

    def _get_instrument_name(self, generator_name: Optional[GeneratorName] = None) -> str:
        if not self.reconstruction_data:
            raise AssertionError("Expected reconstruction data to be present")

        reconstruction = self.reconstruction_data.reconstruction
        filename = to_path(reconstruction.audio_filepath).stem
        if generator_name is None:
            return filename

        instrument_name = f"{filename}_{generator_name}"
        return instrument_name

    def export_instrument_dialog(self, generator_name: GeneratorName) -> None:
        if not self.reconstruction_data:
            raise AssertionError("Expected reconstruction data to be loaded before exporting FTI")

        reconstruction = self.reconstruction_data.reconstruction
        feature_data = self.reconstruction_data.feature_data
        if generator_name not in feature_data.generators:
            return

        filename = to_path(reconstruction.audio_filepath).stem
        instrument_name = f"{filename} ({generator_name})"

        self._pending_generator_name = generator_name
        with dpg.file_dialog(
            label=TTL_DIALOG_EXPORT_FTI,
            width=DIM_DIALOG_WIDTH_FILE,
            height=DIM_DIALOG_HEIGHT_FILE,
            callback=self._handle_export_instrument,
            file_count=VAL_DIALOG_GLOBAL_FILE_COUNT_SINGLE,
            default_filename=instrument_name,
            default_path=str(self.application_config_manager.get_instrument_path()),
        ):
            dpg.add_file_extension(EXT_FILE_INSTRUMENT)

    @file_dialog_handler
    def _handle_export_instrument(self, filepath: Path) -> None:
        if not self.reconstruction_data or not self._pending_generator_name:
            logger.warning("No reconstruction data available for FTI export")
            self._pending_generator_name = None
            return

        generator_name = self._pending_generator_name
        instrument_name = self._get_instrument_name(generator_name)
        self._pending_generator_name = None

        try:
            self.save_instrument_feature(filepath, instrument_name, generator_name)
            logger.info(f"Exported instrument feature to FTI: {filepath}")
            show_message_with_path_dialog(
                TTL_DIALOG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_STATUS,
                MSG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_FTI_SUCCESS,
                filepath,
            )
        except (FileNotFoundError, IOError, IsADirectoryError, PermissionError, OSError) as exception:
            logger.error_with_traceback(exception, f"File error while saving instrument: {filepath}")
            show_error_dialog(exception, MSG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_FTI_FAILED)
        except Exception as exception:  # TODO: specify exception type
            logger.error_with_traceback(exception, f"Failed to export instrument: {filepath}")
            show_error_dialog(exception, MSG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_FTI_FAILED)

        self.application_config_manager.set_instrument_path(filepath.parent)

    @file_dialog_handler
    def _handle_export_instruments(self, directory: Path) -> None:
        if not self.reconstruction_data:
            logger.warning("No reconstruction data available for FTIs export")
            return

        try:
            self.save_instrument_features(directory)
            logger.info(f"Exported instrument features to FTI: {directory}")
            show_message_with_path_dialog(
                TTL_DIALOG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_STATUS,
                MSG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_FTIS_SUCCESS,
                directory,
            )
        except (FileNotFoundError, IOError, IsADirectoryError, PermissionError, OSError) as exception:
            logger.error_with_traceback(exception, f"File error while saving instruments: {directory}")
            show_error_dialog(exception, MSG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_FTIS_FAILED)
        except Exception as exception:  # TODO: specify exception type
            logger.error_with_traceback(exception, f"Failed to export instruments: {directory}")
            show_error_dialog(exception, MSG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_FTIS_FAILED)

        self.application_config_manager.set_instrument_path(directory.parent)

    def export_instruments_dialog(self) -> None:
        if not self.reconstruction_data:
            raise AssertionError("Expected reconstruction data to be loaded before exporting FTI")

        with dpg.file_dialog(
            label=TTL_DIALOG_EXPORT_FTI,
            width=DIM_DIALOG_WIDTH_FILE,
            height=DIM_DIALOG_HEIGHT_FILE,
            callback=self._handle_export_instruments,
            file_count=VAL_DIALOG_GLOBAL_FILE_COUNT_SINGLE,
            directory_selector=True,
            default_filename=self._get_instrument_name(),
            default_path=str(self.application_config_manager.get_instrument_path()),
        ):
            pass

    def save_instrument_features(self, directory: Path) -> None:
        if not self.reconstruction_data:
            raise AssertionError("Expected reconstruction data to be loaded before exporting all FTI instruments")

        directory.mkdir(parents=True, exist_ok=True)
        for generator_name in self.reconstruction_data.feature_data.generators.keys():
            instrument_name = self._get_instrument_name(generator_name)
            filepath = directory / f"{instrument_name}{EXT_FILE_INSTRUMENT}"
            self.save_instrument_feature(filepath, instrument_name, generator_name)

    def save_instrument_feature(
        self,
        filepath: Path,
        instrument_name: str,
        generator_name: GeneratorName,
    ) -> None:
        if not self.reconstruction_data:
            raise AssertionError("Expected reconstruction data to be loaded before exporting an FTI instrument")

        feature = self.reconstruction_data.feature_data[generator_name]
        feature.save(filepath, instrument_name)

    def _handle_export_wav_button_click(self) -> None:
        if self._on_export_wav:
            self._on_export_wav()

    def export_reconstruction_wav_dialog(self) -> None:
        if not self.reconstruction_data:
            raise AssertionError("Expected reconstruction data to be loaded before exporting to WAV")

        reconstruction = self.reconstruction_data.reconstruction
        filename = to_path(reconstruction.audio_filepath).stem

        with dpg.file_dialog(
            label=TTL_DIALOG_EXPORT_WAV,
            width=DIM_DIALOG_WIDTH_FILE,
            height=DIM_DIALOG_HEIGHT_FILE,
            callback=self._handle_wav_export,
            file_count=VAL_DIALOG_GLOBAL_FILE_COUNT_SINGLE,
            default_filename=filename,
            default_path=str(self.application_config_manager.get_audio_path()),
        ):
            dpg.add_file_extension(EXT_FILE_WAVE)

    @file_dialog_handler
    def _handle_wav_export(self, filepath: Path) -> None:
        if not self.reconstruction_data:
            return

        selected_generators = self._get_selected_generators()
        partial_approximation = self.reconstruction_data.get_partials(selected_generators)
        sample_rate = self.reconstruction_data.reconstruction.config.library.sample_rate

        try:
            write_wave(filepath, sample_rate, partial_approximation)
            logger.info(f"Exported reconstruction to WAV: {filepath}")
            show_message_with_path_dialog(
                TTL_DIALOG_EXPORT_WAV,
                MSG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_WAV_SUCCESS,
                filepath,
            )
        except Exception as exception:  # TODO: specify exception type
            logger.error_with_traceback(exception, f"Failed to export reconstruction to WAV: {filepath}")
            show_error_dialog(exception, MSG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_WAV_FAILED)

        self.application_config_manager.set_audio_path(filepath)
