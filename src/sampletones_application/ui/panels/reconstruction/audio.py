from pathlib import Path
from typing import Callable, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.global_ import (
    StatusElements,
)
from sampletones_application.categories.elements.reconstructions import (
    ReconstructionPanelElements,
    ReconstructionsInstrumentsElements,
)
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.general import PathColors
from sampletones_application.tags.reconstructions import (
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_GROUP_AUDIO_SOURCE,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_PANEL_AUDIO,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_PATH_ORIGINAL_AUDIO,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_PATH_RECONSTRUCTION_FILE,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_RADIO_AUDIO_SOURCE,
)
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.elements.path import GUIPathText
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.utils.color import RGBA
from sampletones_application.utils.file import file_dialog_handler
from sampletones_application.utils.gui.dpg import dpg_configure_item, dpg_set_value
from sampletones_application.view_model.reconstruction.reconstruction import (
    ReconstructionPathState,
    ReconstructionPathViewModel,
    ReconstructionViewModel,
)
from sampletones_core.constants.enums import AudioSourceType
from sampletones_core.paths import EXT_FILE_INSTRUMENT, EXT_FILE_WAVE
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import PathCallback


class GUIReconstructionAudioPanel(GUIPanel):
    def __init__(
        self,
        *,
        path_colors: PathColors,
        path_status_color: RGBA,
        file_dialog_width: int,
        file_dialog_height: int,
        initial_collapsed: bool = False,
        language_manager: LanguageManager,
        status_bar: GUIStatusBar,
    ) -> None:
        self._status_bar = status_bar
        self._path_colors = path_colors
        self._path_status_color = path_status_color
        self._file_dialog_width = file_dialog_width
        self._file_dialog_height = file_dialog_height

        self._reconstruction_file_path: GUIPathText
        self._original_audio_path: GUIPathText

        self.on_audio_source_changed: Optional[Callable[[AudioSourceType], None]] = None
        self.on_export_instrument_confirmed: Optional[PathCallback] = None
        self.on_export_instruments_confirmed: Optional[PathCallback] = None
        self.on_export_wav_confirmed: Optional[PathCallback] = None

        self._lbl_audio_source = language_manager[
            Page.RECONSTRUCTIONS,
            Panel.RECONSTRUCTION,
            TextType.LABEL,
            ReconstructionPanelElements.AUDIO_SOURCE_LABEL,
        ]
        self._load_path_text(language_manager)
        self._lbl_original_audio_radio = language_manager[
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
        self._ttl_export_wav = language_manager[
            Page.RECONSTRUCTIONS,
            Panel.INSTRUMENTS,
            TextType.TITLE,
            ReconstructionsInstrumentsElements.EXPORT_WAV_DIALOG,
        ]
        self._ttl_export_instrument = language_manager[
            Page.RECONSTRUCTIONS,
            Panel.INSTRUMENTS,
            TextType.TITLE,
            ReconstructionsInstrumentsElements.EXPORT_INSTRUMENT_DIALOG,
        ]
        self._ttl_export_instruments = language_manager[
            Page.RECONSTRUCTIONS,
            Panel.INSTRUMENTS,
            TextType.TITLE,
            ReconstructionsInstrumentsElements.EXPORT_INSTRUMENTS_DIALOG,
        ]

        super().__init__(
            tag=TAG_RECONSTRUCTIONS_RECONSTRUCTION_PANEL_AUDIO,
        )
        self._enable_vertical_collapse(initial_collapsed=initial_collapsed, auto_height=True)

    def _load_path_text(self, language_manager: LanguageManager) -> None:
        self._lbl_reconstruction_file = language_manager[
            Page.RECONSTRUCTIONS,
            Panel.RECONSTRUCTION,
            TextType.LABEL,
            ReconstructionPanelElements.RECONSTRUCTION_FILE_LABEL,
        ]
        self._lbl_original_audio = language_manager[
            Page.RECONSTRUCTIONS,
            Panel.RECONSTRUCTION,
            TextType.LABEL,
            ReconstructionPanelElements.ORIGINAL_AUDIO_LABEL,
        ]
        self._msg_path_not_found = language_manager[
            Page.RECONSTRUCTIONS,
            Panel.RECONSTRUCTION,
            TextType.LABEL,
            ReconstructionPanelElements.PATH_NOT_FOUND,
        ]
        self._msg_path_not_applicable = language_manager[
            Page.RECONSTRUCTIONS,
            Panel.RECONSTRUCTION,
            TextType.LABEL,
            ReconstructionPanelElements.PATH_NOT_APPLICABLE,
        ]
        self._msg_path_status = language_manager[
            Page.GLOBAL,
            Panel.STATUS,
            TextType.MESSAGE,
            StatusElements.PATH,
        ]

    def create_panel(self, parent: str) -> None:
        with self._collapsible_card(
            parent,
            self._lbl_audio_source,
            glyph=self._glyphs.headers.source,
            width=0,
            no_scrollbar=True,
        ):
            self._create_audio_source_radio_buttons()
            dpg.add_separator()
            self._create_path_display()

    def update_view(self, view_model: ReconstructionViewModel) -> None:
        self._render_path(self._reconstruction_file_path, view_model.reconstruction_file)
        self._render_path(self._original_audio_path, view_model.original_audio)

        dpg_configure_item(
            TAG_RECONSTRUCTIONS_RECONSTRUCTION_GROUP_AUDIO_SOURCE,
            enabled=view_model.audio_source_enabled,
        )
        if not view_model.audio_source_enabled:
            dpg_set_value(TAG_RECONSTRUCTIONS_RECONSTRUCTION_RADIO_AUDIO_SOURCE, self._lbl_reconstruction_radio)

    def open_export_instrument_dialog(self, default_filename: str, default_path: str) -> None:
        with dpg.file_dialog(
            label=self._ttl_export_instrument,
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
            label=self._ttl_export_instruments,
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

    def _render_path(self, path_widget: GUIPathText, view_model: ReconstructionPathViewModel) -> None:
        match view_model.state:
            case ReconstructionPathState.AVAILABLE:
                path_widget.set_path(view_model.path)
            case ReconstructionPathState.NOT_FOUND:
                path_widget.set_status(self._msg_path_not_found, self._path_status_color)
            case ReconstructionPathState.NOT_APPLICABLE:
                path_widget.set_status(self._msg_path_not_applicable, self._path_status_color)
            case ReconstructionPathState.EMPTY:
                path_widget.set_status("", self._path_status_color)

    def _create_path_display(self) -> None:
        self._reconstruction_file_path = GUIPathText(
            tag=TAG_RECONSTRUCTIONS_RECONSTRUCTION_PATH_RECONSTRUCTION_FILE,
            path=None,
            parent=self._body_container,
            color=self._path_colors.default,
            hover_color=self._path_colors.hover,
            status_message=self._msg_path_status,
            prefix=self._lbl_reconstruction_file,
            font=Font.REGULAR_SMALL,
            status_bar=self._status_bar,
        )
        self._original_audio_path = GUIPathText(
            tag=TAG_RECONSTRUCTIONS_RECONSTRUCTION_PATH_ORIGINAL_AUDIO,
            path=None,
            parent=self._body_container,
            color=self._path_colors.default,
            hover_color=self._path_colors.hover,
            status_message=self._msg_path_status,
            prefix=self._lbl_original_audio,
            font=Font.REGULAR_SMALL,
            status_bar=self._status_bar,
        )

        self._reconstruction_file_path.set_status("", self._path_status_color)
        self._original_audio_path.set_status("", self._path_status_color)

    def _create_audio_source_radio_buttons(self) -> None:
        with dpg.group(
            tag=TAG_RECONSTRUCTIONS_RECONSTRUCTION_GROUP_AUDIO_SOURCE,
            parent=self._body_container,
        ):
            dpg.add_radio_button(
                items=[
                    self._lbl_reconstruction_radio,
                    self._lbl_original_audio_radio,
                ],
                tag=TAG_RECONSTRUCTIONS_RECONSTRUCTION_RADIO_AUDIO_SOURCE,
                default_value=self._lbl_reconstruction_radio,
                callback=self._on_audio_source_changed,
                horizontal=True,
            )
            FontRegistry.bind_to_item(TAG_RECONSTRUCTIONS_RECONSTRUCTION_RADIO_AUDIO_SOURCE, Font.REGULAR_SMALL)

        dpg_configure_item(TAG_RECONSTRUCTIONS_RECONSTRUCTION_GROUP_AUDIO_SOURCE, enabled=False)

    def _on_audio_source_changed(self, sender: Sender, app_data: str) -> None:
        if app_data == self._lbl_original_audio_radio:
            audio_source = AudioSourceType.ORIGINAL
        else:
            audio_source = AudioSourceType.RECONSTRUCTION

        self.call(self.on_audio_source_changed, audio_source)

    @file_dialog_handler
    def _handle_export_instrument(self, filepath: Path) -> None:
        self.call(self.on_export_instrument_confirmed, filepath)

    @file_dialog_handler
    def _handle_export_instruments(self, filepath: Path) -> None:
        self.call(self.on_export_instruments_confirmed, filepath)

    @file_dialog_handler
    def _handle_wav_export(self, filepath: Path) -> None:
        self.call(self.on_export_wav_confirmed, filepath)
