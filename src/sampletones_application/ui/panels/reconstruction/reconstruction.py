from pathlib import Path
from typing import Any, Callable, List, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.global_ import (
    ContextElements,
    GlobalTemplateElements,
)
from sampletones_application.categories.elements.reconstructions import (
    ReconstructionPanelElements,
    ReconstructionsDetailsElements,
)
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.general import (
    SUF_PANEL_CENTER,
    TAG_GLOBAL_TAB_RECONSTRUCTIONS,
)
from sampletones_application.constants.reconstructions import (
    PRE_RECONSTRUCTION_GENERATOR,
    SUF_RECONSTRUCTIONS_RECONSTRUCTION_AUDIO,
    SUF_RECONSTRUCTIONS_RECONSTRUCTION_AUTOSCALE,
    SUF_RECONSTRUCTIONS_RECONSTRUCTION_PLOT_WINDOW,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_BUTTON_EXPORT_WAV,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_BUTTON_LOCATE_ORIGINAL_AUDIO,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_GROUP_AUDIO_SOURCE,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_GROUP_GENERATORS,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_PANEL,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_PANEL_PLAYER,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_PANEL_WAVEFORM,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_RADIO_AUDIO_SOURCE,
)
from sampletones_application.layout.graphs import GraphsLayout
from sampletones_application.layout.player import PlayerLayout
from sampletones_application.logic.reconstruction.data import (
    ReconstructionData,
)
from sampletones_application.logic.shared.player import PlayerLogic
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.graphs.waveform import GUIWaveformGraph
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.panels.player import GUIAudioPlayerPanel
from sampletones_application.utils.file import file_dialog_handler
from sampletones_application.utils.gui.dialogs import DialogsRenderer
from sampletones_application.utils.gui.dpg import dpg_configure_item, dpg_set_value
from sampletones_application.utils.gui.tooltip import show_tooltip
from sampletones_application.view_model.reconstruction.reconstruction import (
    ReconstructionViewModel,
)
from sampletones_application.view_model.shared.audio_data import AudioData
from sampletones_core.constants.enums import AudioSourceType, GeneratorName
from sampletones_core.paths import EXT_FILE_INSTRUMENT, EXT_FILE_WAVE
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import (
    MessageCallback,
    PathCallback,
    VoidCallback,
)


class GUIReconstructionPanel(GUIPanel):
    def __init__(
        self,
        player_logic: PlayerLogic,
        *,
        layout_graphs: GraphsLayout,
        layout_player: PlayerLayout,
        file_dialog_width: int,
        file_dialog_height: int,
        language_manager: LanguageManager,
        dialogs: DialogsRenderer,
    ) -> None:
        self._player_logic = player_logic
        self._layout_graphs = layout_graphs
        self._file_dialog_width = file_dialog_width
        self._file_dialog_height = file_dialog_height
        self._layout_player = layout_player
        self._dialogs = dialogs

        self.waveform_display: GUIWaveformGraph
        self.player_panel: GUIAudioPlayerPanel

        self._frame_length: Optional[int] = None

        self.on_audio_source_changed: Optional[Callable[[AudioSourceType], None]] = None
        self.on_generators_changed: Optional[Callable[[List[GeneratorName]], None]] = None
        self.on_export_wav_requested: Optional[VoidCallback] = None
        self.on_export_instrument_confirmed: Optional[PathCallback] = None
        self.on_export_instruments_confirmed: Optional[PathCallback] = None
        self.on_export_wav_confirmed: Optional[PathCallback] = None
        self.on_locate_original_audio_requested: Optional[VoidCallback] = None

        self.audio_tag = f"{TAG_RECONSTRUCTIONS_RECONSTRUCTION_PANEL}{SUF_RECONSTRUCTIONS_RECONSTRUCTION_AUDIO}"
        self.plot_tag = f"{TAG_RECONSTRUCTIONS_RECONSTRUCTION_PANEL}{SUF_RECONSTRUCTIONS_RECONSTRUCTION_PLOT_WINDOW}"
        self.autoscale_tag = f"{self.plot_tag}{SUF_RECONSTRUCTIONS_RECONSTRUCTION_AUTOSCALE}"

        self._lbl_audio_source = language_manager[
            Page.RECONSTRUCTIONS,
            Panel.RECONSTRUCTION,
            TextType.LABEL,
            ReconstructionPanelElements.AUDIO_SOURCE_LABEL,
        ]
        self._lbl_autoscale = language_manager[
            Page.RECONSTRUCTIONS,
            Panel.RECONSTRUCTION,
            TextType.LABEL,
            ReconstructionPanelElements.AUTOSCALE_CHECKBOX,
        ]
        self._lbl_export_wav = language_manager[
            Page.RECONSTRUCTIONS,
            Panel.RECONSTRUCTION,
            TextType.LABEL,
            ReconstructionPanelElements.EXPORT_WAV_BUTTON,
        ]
        self._lbl_locate_audio = language_manager[
            Page.RECONSTRUCTIONS,
            Panel.RECONSTRUCTION,
            TextType.LABEL,
            ReconstructionPanelElements.LOCATE_AUDIO_BUTTON,
        ]
        self._lbl_original_audio = language_manager[
            Page.RECONSTRUCTIONS,
            Panel.RECONSTRUCTION,
            TextType.LABEL,
            ReconstructionPanelElements.ORIGINAL_AUDIO_RADIO,
        ]
        self._lbl_reconstruction_radio = language_manager[
            Page.RECONSTRUCTIONS,
            Panel.RECONSTRUCTION,
            TextType.LABEL,
            ReconstructionPanelElements.RECONSTRUCTION_RADIO,
        ]
        self._lbl_waveform = language_manager[
            Page.RECONSTRUCTIONS,
            Panel.RECONSTRUCTION,
            TextType.LABEL,
            ReconstructionPanelElements.WAVEFORM_LABEL,
        ]
        self._tooltip_autoscale = language_manager[
            Page.RECONSTRUCTIONS,
            Panel.RECONSTRUCTION,
            TextType.TOOLTIP,
            ReconstructionPanelElements.AUTOSCALE_TOOLTIP,
        ]
        self._msg_generator_toggle = language_manager[
            Page.RECONSTRUCTIONS,
            Panel.DETAILS,
            TextType.MESSAGE,
            ReconstructionsDetailsElements.STATUS_GENERATOR_TOGGLE,
        ]
        self._msg_generator_not_available = language_manager[
            Page.RECONSTRUCTIONS,
            Panel.DETAILS,
            TextType.MESSAGE,
            ReconstructionsDetailsElements.STATUS_GENERATOR_NOT_AVAILABLE,
        ]
        self._ttl_export_wav = language_manager[
            Page.RECONSTRUCTIONS,
            Panel.DETAILS,
            TextType.TITLE,
            ReconstructionsDetailsElements.EXPORT_WAV_DIALOG,
        ]
        self._ttl_export_fti = language_manager[
            Page.RECONSTRUCTIONS,
            Panel.DETAILS,
            TextType.TITLE,
            ReconstructionsDetailsElements.EXPORT_FTI_DIALOG,
        ]
        self._lbl_pulse_1 = language_manager[
            Page.GLOBAL,
            Panel.CONTEXT,
            TextType.LABEL,
            ContextElements.PULSE_1,
        ]
        self._lbl_pulse_2 = language_manager[
            Page.GLOBAL,
            Panel.CONTEXT,
            TextType.LABEL,
            ContextElements.PULSE_2,
        ]
        self._lbl_triangle = language_manager[
            Page.GLOBAL,
            Panel.CONTEXT,
            TextType.LABEL,
            ContextElements.TRIANGLE,
        ]
        self._lbl_noise = language_manager[
            Page.GLOBAL,
            Panel.CONTEXT,
            TextType.LABEL,
            ContextElements.NOISE,
        ]
        self._val_text_on = language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.TEMPLATE,
            GlobalTemplateElements.ON,
        ]
        self._val_text_off = language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.TEMPLATE,
            GlobalTemplateElements.OFF,
        ]
        self._language_manager = language_manager

        super().__init__(
            tag=TAG_RECONSTRUCTIONS_RECONSTRUCTION_PANEL,
            parent=f"{TAG_GLOBAL_TAB_RECONSTRUCTIONS}{SUF_PANEL_CENTER}",
        )

    def create_panel(self) -> None:
        self._create_player_panel()
        self._create_audio_panel()
        self._create_plot_panel()

    def update_view(self, view_model: ReconstructionViewModel) -> None:
        for generator_name in GeneratorName:
            tag = self._get_generator_checkbox_tag(generator_name)
            is_available = generator_name in view_model.available_generators
            dpg_configure_item(tag, enabled=is_available, default_value=is_available)
            dpg_set_value(tag, is_available)

        dpg_configure_item(
            TAG_RECONSTRUCTIONS_RECONSTRUCTION_RADIO_AUDIO_SOURCE, enabled=view_model.audio_source_enabled
        )
        if not view_model.audio_source_enabled:
            dpg_set_value(TAG_RECONSTRUCTIONS_RECONSTRUCTION_RADIO_AUDIO_SOURCE, self._lbl_reconstruction_radio)

        dpg_configure_item(
            TAG_RECONSTRUCTIONS_RECONSTRUCTION_BUTTON_EXPORT_WAV,
            enabled=view_model.buttons_enabled,
        )
        dpg_configure_item(
            TAG_RECONSTRUCTIONS_RECONSTRUCTION_BUTTON_LOCATE_ORIGINAL_AUDIO,
            enabled=view_model.buttons_enabled,
        )

    def load_waveform_data(
        self,
        reconstruction_data: ReconstructionData,
        generators: List[GeneratorName],
    ) -> None:
        self._frame_length = reconstruction_data.reconstruction.config.frame_length
        self.waveform_display.load_reconstruction_data(reconstruction_data, generators)

    def set_waveform_top_source(self, audio_source: AudioSourceType) -> None:
        self.waveform_display.set_top_source(audio_source)

    def update_waveform_data(
        self,
        reconstruction_data: ReconstructionData,
        generators: List[GeneratorName],
    ) -> None:
        self.waveform_display.update_reconstruction_data(reconstruction_data, generators)

    def update_audio_data(self, audio_data: Optional[AudioData]) -> None:
        if audio_data is None:
            self.player_panel.clear_audio()
        else:
            self.player_panel.load_audio_data(audio_data)

    def clear_waveform(self) -> None:
        self._frame_length = None
        self.waveform_display.clear()

    def open_export_instrument_dialog(self, default_filename: str, default_path: str) -> None:
        with dpg.file_dialog(
            label=self._ttl_export_fti,
            width=self._file_dialog_width,
            height=self._file_dialog_height,
            callback=self._handle_export_instrument,
            file_count=1,
            default_filename=default_filename,
            default_path=default_path,
        ):
            dpg.add_file_extension(EXT_FILE_INSTRUMENT)

    def open_export_instruments_dialog(self, default_filename: str, default_path: str) -> None:
        with dpg.file_dialog(
            label=self._ttl_export_fti,
            width=self._file_dialog_width,
            height=self._file_dialog_height,
            callback=self._handle_export_instruments,
            file_count=1,
            directory_selector=True,
            default_filename=default_filename,
            default_path=default_path,
        ):
            pass

    def open_export_wav_dialog(self, default_filename: str, default_path: str) -> None:
        with dpg.file_dialog(
            label=self._ttl_export_wav,
            width=self._file_dialog_width,
            height=self._file_dialog_height,
            callback=self._handle_wav_export,
            file_count=1,
            default_filename=default_filename,
            default_path=default_path,
        ):
            dpg.add_file_extension(EXT_FILE_WAVE)

    def set_overlay(self, index: Optional[int]) -> None:
        if self._frame_length is None:
            return

        if index is None:
            self.waveform_display.set_overlay_range(0, 0)
            return

        start = index * self._frame_length
        end = start + self._frame_length
        self.waveform_display.set_overlay_range(start, end)

    def play(self) -> None:
        self.player_panel.play()

    def pause_or_resume(self) -> None:
        self.player_panel.pause_or_resume()

    def stop(self) -> None:
        self.player_panel.stop()

    def is_playing(self) -> bool:
        return self.player_panel.is_playing()

    def is_paused(self) -> bool:
        return self.player_panel.is_paused()

    def is_loaded(self) -> bool:
        return self.player_panel.is_loaded()

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
            self._create_locate_original_audio_button()
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
            self._create_autoscale_checkbox()
            self._create_waveform_display()
            self._create_generator_checkboxes()
            self._create_tooltips()

        dpg_configure_item(TAG_RECONSTRUCTIONS_RECONSTRUCTION_BUTTON_EXPORT_WAV, enabled=False)
        dpg_configure_item(
            TAG_RECONSTRUCTIONS_RECONSTRUCTION_BUTTON_LOCATE_ORIGINAL_AUDIO,
            enabled=False,
        )

    def _create_player_panel(self) -> None:
        self.player_panel = GUIAudioPlayerPanel(
            tag=TAG_RECONSTRUCTIONS_RECONSTRUCTION_PANEL_PLAYER,
            parent=self.parent,
            player_logic=self._player_logic,
            on_position_changed=self._on_player_position_changed,
            layout=self._layout_player,
            language_manager=self._language_manager,
            dialogs=self._dialogs,
        )

    def _create_audio_source_radio_buttons(self) -> None:
        dpg.add_text(self._lbl_audio_source)
        with dpg.group(
            tag=TAG_RECONSTRUCTIONS_RECONSTRUCTION_GROUP_AUDIO_SOURCE,
            parent=self.audio_tag,
            horizontal=True,
        ):
            dpg.add_radio_button(
                items=[
                    self._lbl_reconstruction_radio,
                    self._lbl_original_audio,
                ],
                tag=TAG_RECONSTRUCTIONS_RECONSTRUCTION_RADIO_AUDIO_SOURCE,
                default_value=self._lbl_reconstruction_radio,
                callback=self._on_audio_source_changed,
                horizontal=True,
                enabled=False,
            )
            FontRegistry.bind_to_item(TAG_RECONSTRUCTIONS_RECONSTRUCTION_RADIO_AUDIO_SOURCE, Font.REGULAR_SMALL)

    def _create_locate_original_audio_button(self) -> None:
        GUIButton(
            label=self._lbl_locate_audio,
            tag=TAG_RECONSTRUCTIONS_RECONSTRUCTION_BUTTON_LOCATE_ORIGINAL_AUDIO,
            parent=self.audio_tag,
            callback=self._handle_locate_original_audio_button_click,
            width=-1,
            enabled=True,
        )

    def _create_export_wav_button(self) -> None:
        GUIButton(
            label=self._lbl_export_wav,
            tag=TAG_RECONSTRUCTIONS_RECONSTRUCTION_BUTTON_EXPORT_WAV,
            parent=self.audio_tag,
            callback=self._handle_export_wav_button_click,
            width=-1,
            enabled=True,
        )

    def _create_autoscale_checkbox(self) -> None:
        dpg.add_checkbox(
            label=self._lbl_autoscale,
            tag=self.autoscale_tag,
            parent=self.plot_tag,
            default_value=True,
            callback=self._on_autoscale_changed,
        )
        FontRegistry.bind_to_item(self.autoscale_tag, Font.REGULAR_SMALL)

    def _create_waveform_display(self) -> None:
        self.waveform_display = GUIWaveformGraph(
            tag=TAG_RECONSTRUCTIONS_RECONSTRUCTION_PANEL_WAVEFORM,
            parent=self.plot_tag,
            layout=self._layout_graphs,
            language_manager=self._language_manager,
            label=self._lbl_waveform,
        )

    def _create_generator_checkboxes(self) -> None:
        generator_labels = {
            GeneratorName.PULSE1: self._lbl_pulse_1,
            GeneratorName.PULSE2: self._lbl_pulse_2,
            GeneratorName.TRIANGLE: self._lbl_triangle,
            GeneratorName.NOISE: self._lbl_noise,
        }

        with dpg.group(
            tag=TAG_RECONSTRUCTIONS_RECONSTRUCTION_GROUP_GENERATORS,
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

    def _create_tooltips(self) -> None:
        show_tooltip(self.autoscale_tag, self._tooltip_autoscale)

    def _create_message_function_for_generator_checkbox(self, generator_name: GeneratorName) -> MessageCallback:
        tag = self._get_generator_checkbox_tag(generator_name)
        name = generator_name.capitalized

        def message_function(*args: Any, **kwargs: Any) -> str:
            if not dpg.is_item_enabled(tag):
                return self._msg_generator_not_available.format(generator_name=name)

            return self._msg_generator_toggle.format(
                generator_name=name,
                on_or_off=(self._val_text_off if dpg.get_value(tag) else self._val_text_on),
            )

        return message_function

    @staticmethod
    def _get_generator_checkbox_tag(generator_name: GeneratorName) -> str:
        return f"{PRE_RECONSTRUCTION_GENERATOR}{generator_name.value}"

    def _read_selected_generators(self) -> List[GeneratorName]:
        selected_generators: List[GeneratorName] = []
        for generator_name in GeneratorName:
            if dpg.get_value(self._get_generator_checkbox_tag(generator_name)):
                selected_generators.append(generator_name)

        return selected_generators

    def _on_generator_checkbox_changed(self) -> None:
        selected_generators = self._read_selected_generators()
        self.call(self.on_generators_changed, selected_generators)

    def _on_audio_source_changed(self, sender: Sender, app_data: str) -> None:
        if app_data == self._lbl_original_audio:
            audio_source = AudioSourceType.ORIGINAL
        else:
            audio_source = AudioSourceType.RECONSTRUCTION

        self.call(self.on_audio_source_changed, audio_source)

    def _handle_locate_original_audio_button_click(self, sender: Sender, app_data: Any, user_data: Any) -> None:
        self.call(self.on_locate_original_audio_requested)

    def _handle_export_wav_button_click(self, sender: Sender, app_data: Any, user_data: Any) -> None:
        self.call(self.on_export_wav_requested)

    @file_dialog_handler
    def _handle_export_instrument(self, filepath: Path) -> None:
        self.call(self.on_export_instrument_confirmed, filepath)

    @file_dialog_handler
    def _handle_export_instruments(self, filepath: Path) -> None:
        self.call(self.on_export_instruments_confirmed, filepath)

    @file_dialog_handler
    def _handle_wav_export(self, filepath: Path) -> None:
        self.call(self.on_export_wav_confirmed, filepath)

    def _on_player_position_changed(self, position: int) -> None:
        self.waveform_display.set_position(position)

    def _on_autoscale_changed(self, sender: Sender, app_data: bool) -> None:
        self.waveform_display.set_autoscale(app_data)
