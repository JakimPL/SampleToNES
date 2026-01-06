from pathlib import Path
from typing import List, Optional

import dearpygui.dearpygui as dpg

from sampletones.audio import AudioDeviceManager, write_wave
from sampletones.constants.enums import AudioSourceType, GeneratorName
from sampletones.constants.paths import EXT_FILE_INSTRUMENT, EXT_FILE_WAVE
from sampletones.typehints import MessageCallback, Sender, VoidCallback
from sampletones.utils import to_path
from sampletones.utils.logger import logger

from ...config.application.manager import ApplicationConfigManager
from ...config.manager import ConfigManager
from ...constants.general import (
    DIM_DIALOG_HEIGHT_FILE,
    DIM_DIALOG_WIDTH_FILE,
    LBL_CHECKBOX_GLOBAL_NOISE,
    LBL_CHECKBOX_GLOBAL_PULSE_1,
    LBL_CHECKBOX_GLOBAL_PULSE_2,
    LBL_CHECKBOX_GLOBAL_TRIANGLE,
    SUF_PANEL_CENTER,
    TAG_TAB_RECONSTRUCTIONS,
    VAL_DIALOG_GLOBAL_FILE_COUNT_SINGLE,
    VAL_TEXT_OFF,
    VAL_TEXT_ON,
)
from ...constants.graphs import DIM_WAVEFORM_HEIGHT, DIM_WAVEFORM_WIDTH
from ...constants.reconstructions import (
    LBL_BUTTON_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_WAV,
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
    MSG_STATUS_RECONSTRUCTIONS_DETAILS_GENERATOR_NOT_AVAILABLE,
    MSG_STATUS_RECONSTRUCTIONS_DETAILS_GENERATOR_TOGGLE,
    SUF_RECONSTRUCTIONS_RECONSTRUCTION_AUDIO,
    SUF_RECONSTRUCTIONS_RECONSTRUCTION_PLOT_WINDOW,
    TAG_BUTTON_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_WAV,
    TAG_GROUP_RECONSTRUCTIONS_RECONSTRUCTION_AUDIO_SOURCE,
    TAG_GROUP_RECONSTRUCTIONS_RECONSTRUCTION_GENERATORS,
    TAG_PANEL_RECONSTRUCTIONS_RECONSTRUCTION,
    TAG_PANEL_RECONSTRUCTIONS_RECONSTRUCTION_PLAYER,
    TAG_PANEL_RECONSTRUCTIONS_RECONSTRUCTION_WAVEFORM,
    TPL_TAG_CHECKBOX_RECONSTRUCTIONS_RECONSTRUCTION_GENERATOR,
    TPL_TAG_RADIO_RECONSTRUCTIONS_RECONSTRUCTION_AUDIO_SOURCE,
    TTL_DIALOG_EXPORT_FTI,
    TTL_DIALOG_EXPORT_WAV,
    TTL_DIALOG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_STATUS,
    VAL_RADIO_RECONSTRUCTIONS_RECONSTRUCTION_AUDIO_SOURCE,
)
from ...elements.button import GUIButton
from ...elements.fonts.font import Font
from ...elements.fonts.registry import FontRegistry
from ...elements.graphs.waveform import GUIWaveformGraph
from ...elements.panel import GUIPanel
from ...elements.status import GUIStatusBar
from ...player.data import AudioData
from ...reconstruction.data import ReconstructionData
from ...reconstruction.manager import ReconstructionManager
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
        reconstruction_manager: ReconstructionManager,
    ) -> None:
        self.config_manager = config_manager
        self.application_config_manager = application_config_manager
        self.audio_device_manager = audio_device_manager
        self.reconstruction_manager = reconstruction_manager

        self.waveform_display: GUIWaveformGraph
        self.player_panel: GUIAudioPlayerPanel

        self.current_audio_source: AudioSourceType = AudioSourceType.RECONSTRUCTION
        self._pending_generator_name: Optional[GeneratorName] = None

        self.on_export_wav: Optional[VoidCallback] = None
        self.on_change_audio_state: Optional[VoidCallback] = None

        self.audio_tag = f"{TAG_PANEL_RECONSTRUCTIONS_RECONSTRUCTION}{SUF_RECONSTRUCTIONS_RECONSTRUCTION_AUDIO}"
        self.plot_tag = f"{TAG_PANEL_RECONSTRUCTIONS_RECONSTRUCTION}{SUF_RECONSTRUCTIONS_RECONSTRUCTION_PLOT_WINDOW}"

        super().__init__(
            tag=TAG_PANEL_RECONSTRUCTIONS_RECONSTRUCTION,
            parent=f"{TAG_TAB_RECONSTRUCTIONS}{SUF_PANEL_CENTER}",
        )

    def create_panel(self) -> None:
        self._create_player_panel()
        self._create_audio_panel()
        self._create_plot_panel()

    def display_reconstruction(self) -> None:
        self._update_generator_checkboxes()
        self._update_reconstruction_display()

    def update_reconstruction(self) -> None:
        self._update_reconstruction_display(reconstruction_only=True)

    def close_reconstruction(self) -> None:
        self.current_audio_source = AudioSourceType.RECONSTRUCTION
        self.player_panel.clear_audio()
        self.waveform_display.clear()
        self._reset_generator_checkboxes()
        self._reset_audio_source_radio()
        self.display_reconstruction()

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
            on_change_audio_state=self.on_change_audio_state,
        )

    def _create_audio_source_radio_buttons(self) -> None:
        dpg.add_text(LBL_TEXT_RECONSTRUCTIONS_RECONSTRUCTION_AUDIO_SOURCE)
        with dpg.group(
            tag=TAG_GROUP_RECONSTRUCTIONS_RECONSTRUCTION_AUDIO_SOURCE,
            parent=self.audio_tag,
            horizontal=True,
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
        self.waveform_display = GUIWaveformGraph(
            tag=TAG_PANEL_RECONSTRUCTIONS_RECONSTRUCTION_WAVEFORM,
            width=DIM_WAVEFORM_WIDTH,
            height=DIM_WAVEFORM_HEIGHT,
            parent=self.plot_tag,
            label=LBL_PLOT_LABEL_RECONSTRUCTIONS_RECONSTRUCION_WAVEFORM,
        )

    def _create_generator_checkboxes(self) -> None:
        generator_labels = {
            GeneratorName.PULSE1: LBL_CHECKBOX_GLOBAL_PULSE_1,
            GeneratorName.PULSE2: LBL_CHECKBOX_GLOBAL_PULSE_2,
            GeneratorName.TRIANGLE: LBL_CHECKBOX_GLOBAL_TRIANGLE,
            GeneratorName.NOISE: LBL_CHECKBOX_GLOBAL_NOISE,
        }

        with dpg.group(
            tag=TAG_GROUP_RECONSTRUCTIONS_RECONSTRUCTION_GENERATORS,
            parent=self.plot_tag,
            horizontal=True,
        ):
            for generator_name, label in generator_labels.items():
                tag = self._get_generator_checkbox_tag(generator_name)
                dpg.add_checkbox(
                    label=label,
                    tag=tag,
                    default_value=False,
                    enabled=False,
                    callback=self._on_generator_checkbox_changed,
                )

                GUIStatusBar.bind_to_item(
                    tag,
                    self._create_message_function_for_generator_checkbox(generator_name),
                )

    def _create_message_function_for_generator_checkbox(self, generator_name: GeneratorName) -> MessageCallback:
        tag = self._get_generator_checkbox_tag(generator_name)
        name = generator_name.capitalized

        def message_function() -> str:
            if dpg.get_item_configuration(tag)["enabled"] is False:
                return MSG_STATUS_RECONSTRUCTIONS_DETAILS_GENERATOR_NOT_AVAILABLE.format(generator_name=name)

            return MSG_STATUS_RECONSTRUCTIONS_DETAILS_GENERATOR_TOGGLE.format(
                generator_name=name,
                on_or_off=(VAL_TEXT_OFF if dpg.get_value(tag) else VAL_TEXT_ON),
            )

        return message_function

    def _get_generator_tag(self, generator_name: GeneratorName) -> str:
        return TPL_TAG_CHECKBOX_RECONSTRUCTIONS_RECONSTRUCTION_GENERATOR.format(generator_name).lower()

    def _get_selected_generators(self) -> List[GeneratorName]:
        selected_generators: List[GeneratorName] = []
        for generator_name in GeneratorName:
            tag = self._get_generator_tag(generator_name)
            if dpg.get_value(tag):
                selected_generators.append(generator_name)

        return selected_generators

    def _get_current_generators(self) -> List[GeneratorName]:
        generators: List[GeneratorName] = []
        for generator_name in GeneratorName:
            tag = self._get_generator_tag(generator_name)
            if dpg.get_value(tag):
                generators.append(generator_name)

        return generators

    def _update_reconstruction_display(self, reconstruction_only: bool = False) -> None:
        if not self.reconstruction_data:
            dpg_configure_item(
                TAG_BUTTON_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_WAV,
                enabled=False,
            )
            return

        if reconstruction_only:
            selected_generators = self._get_current_generators()
            self.waveform_display.update_reconstruction_data(self.reconstruction_data, selected_generators)
        else:
            selected_generators = self._get_selected_generators()
            self.waveform_display.load_reconstruction_data(self.reconstruction_data, selected_generators)

        self._update_audio_player(reconstruction_only=reconstruction_only)
        dpg_configure_item(
            TAG_BUTTON_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_WAV,
            enabled=True,
        )

    def _on_generator_checkbox_changed(self) -> None:
        self._update_reconstruction_display()

    def _on_audio_source_changed(self, sender: Sender, app_data: str) -> None:
        if app_data == LBL_RADIO_RECONSTRUCTIONS_RECONSTRUCTION_ORIGINAL_AUDIO:
            self.current_audio_source = AudioSourceType.ORIGINAL
        else:
            self.current_audio_source = AudioSourceType.RECONSTRUCTION
        self._update_audio_player()

    # TODO: move audio logic to the player panel
    def _update_audio_player(self, reconstruction_only: bool = False) -> None:
        if not self.reconstruction_data or (
            self.current_audio_source == AudioSourceType.ORIGINAL and reconstruction_only
        ):
            return

        sample_rate = self.reconstruction_data.reconstruction.config.sample_rate
        if self.current_audio_source == AudioSourceType.ORIGINAL:
            audio_data = AudioData.from_array(self.reconstruction_data.original_audio, sample_rate)
        else:
            selected_generators = self._get_selected_generators()
            partial_approximation = self.reconstruction_data.get_partials(selected_generators)
            audio_data = AudioData.from_array(partial_approximation, sample_rate)

        self.player_panel.load_audio_data(audio_data)

    def _update_generator_checkboxes(self) -> None:
        radio_tag = TPL_TAG_RADIO_RECONSTRUCTIONS_RECONSTRUCTION_AUDIO_SOURCE.format(
            VAL_RADIO_RECONSTRUCTIONS_RECONSTRUCTION_AUDIO_SOURCE
        )

        if not self.reconstruction_data:
            dpg_configure_item(radio_tag, enabled=False)
            return

        available_generators = set(self.reconstruction_data.reconstruction.instructions.keys())
        for generator_name in GeneratorName:
            tag = TPL_TAG_CHECKBOX_RECONSTRUCTIONS_RECONSTRUCTION_GENERATOR.format(generator_name)
            is_available = generator_name in available_generators

            dpg_configure_item(tag, enabled=is_available, default_value=is_available)
            if is_available:
                dpg_set_value(tag, True)

        dpg_configure_item(radio_tag, enabled=True)

    def _get_generator_checkbox_tag(self, generator_name: GeneratorName) -> str:
        return TPL_TAG_CHECKBOX_RECONSTRUCTIONS_RECONSTRUCTION_GENERATOR.format(generator_name.value)

    def _reset_generator_checkboxes(self) -> None:
        for generator_name in GeneratorName:
            tag = self._get_generator_checkbox_tag(generator_name)
            dpg.configure_item(tag, enabled=False, default_value=False)
            dpg.set_value(tag, False)

    def _reset_audio_source_radio(self) -> None:
        radio_tag = TPL_TAG_RADIO_RECONSTRUCTIONS_RECONSTRUCTION_AUDIO_SOURCE.format(
            VAL_RADIO_RECONSTRUCTIONS_RECONSTRUCTION_AUDIO_SOURCE
        )
        dpg.configure_item(radio_tag, enabled=False)
        dpg.set_value(radio_tag, LBL_RADIO_RECONSTRUCTIONS_RECONSTRUCTION_AUDIO)
        dpg.configure_item(TAG_BUTTON_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_WAV, enabled=False)

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
            logger.info(f"Exported instrument feature to FTI: {logger.format_path(filepath)}")
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
            logger.info(f"Exported instrument features to FTI: {logger.format_path(directory)}")
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
        self.call(self.on_export_wav)

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
            logger.info(f"Exported reconstruction to WAV: {logger.format_path(filepath)}")
            show_message_with_path_dialog(
                TTL_DIALOG_EXPORT_WAV,
                MSG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_WAV_SUCCESS,
                filepath,
            )
        except Exception as exception:  # TODO: specify exception type
            logger.error_with_traceback(exception, f"Failed to export reconstruction to WAV: {filepath}")
            show_error_dialog(exception, MSG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_WAV_FAILED)

        self.application_config_manager.set_audio_path(filepath)

    def set_overlay(self, index: Optional[int]) -> None:
        if self.reconstruction_data is None:
            return

        if index is None:
            self.waveform_display.set_overlay_range(0, 0)
            return

        frame_length = self.reconstruction_data.reconstruction.config.frame_length
        start = index * frame_length
        end = start + frame_length
        self.waveform_display.set_overlay_range(start, end)

    @property
    def reconstruction_data(self) -> Optional[ReconstructionData]:
        return self.reconstruction_manager.current_reconstruction
