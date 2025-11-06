from pathlib import Path
from typing import Callable, Optional, Union

import dearpygui.dearpygui as dpg

from browser.config.manager import ConfigManager
from browser.converter.converter import ReconstructionConverter
from browser.utils import show_modal_dialog
from constants.browser import (
    CLR_CONVERTER_PATH_TEXT,
    DIM_CONVERTER_BUTTON_SPACING,
    DIM_CONVERTER_BUTTON_WIDTH,
    DIM_DIALOG_CONVERTER_HEIGHT,
    DIM_DIALOG_CONVERTER_WIDTH,
    LBL_BUTTON_CANCEL,
    LBL_BUTTON_LOAD,
    MSG_CONVERTER_CONFIG_NOT_AVAILABLE,
    MSG_CONVERTER_ERROR_PREFIX,
    MSG_CONVERTER_IDLE,
    MSG_CONVERTER_SUCCESS,
    SUF_CONVERTER_HANDLER,
    TAG_CONVERTER_CANCEL_BUTTON,
    TAG_CONVERTER_ERROR_DIALOG,
    TAG_CONVERTER_LOAD_BUTTON,
    TAG_CONVERTER_PATH_TEXT,
    TAG_CONVERTER_PROGRESS,
    TAG_CONVERTER_STATUS,
    TAG_CONVERTER_SUCCESS_DIALOG,
    TAG_CONVERTER_WINDOW,
    TITLE_DIALOG_CONVERTER,
    TITLE_DIALOG_ERROR,
    VAL_GLOBAL_DEFAULT_FLOAT,
)


class GUIConverterWindow:
    def __init__(
        self, config_manager: ConfigManager, on_load_callback: Optional[Callable[[Path], None]] = None
    ) -> None:
        self.config_manager = config_manager
        self.on_load_callback = on_load_callback
        self.converter: Optional[ReconstructionConverter] = None
        self.target_path: Optional[Path] = None
        self.is_file: bool = False
        self.output_file_path: Optional[Path] = None

    def show(self, target_path: Union[str, Path], is_file: bool = False) -> None:
        self.target_path = Path(target_path)
        self.is_file = is_file
        self.output_file_path = None

        config = self.config_manager.get_config()
        if not config:
            self._show_error_dialog(MSG_CONVERTER_CONFIG_NOT_AVAILABLE)
            return

        if dpg.does_item_exist(TAG_CONVERTER_WINDOW):
            dpg.delete_item(TAG_CONVERTER_WINDOW)

        self.converter = ReconstructionConverter(
            config=config,
            on_complete=self._on_conversion_complete,
            on_error=self._on_conversion_error,
        )

        with dpg.window(
            label=TITLE_DIALOG_CONVERTER,
            tag=TAG_CONVERTER_WINDOW,
            modal=True,
            width=DIM_DIALOG_CONVERTER_WIDTH,
            height=DIM_DIALOG_CONVERTER_HEIGHT,
            no_resize=True,
            on_close=self._on_close,
        ):
            dpg.add_text(MSG_CONVERTER_IDLE, tag=TAG_CONVERTER_STATUS)
            dpg.add_progress_bar(
                tag=TAG_CONVERTER_PROGRESS,
                default_value=VAL_GLOBAL_DEFAULT_FLOAT,
                width=-1,
            )
            dpg.add_text(
                str(self.target_path),
                tag=TAG_CONVERTER_PATH_TEXT,
                color=CLR_CONVERTER_PATH_TEXT,
            )
            dpg.bind_item_handler_registry(TAG_CONVERTER_PATH_TEXT, self._create_path_handler())

            dpg.add_separator()

            with dpg.group(horizontal=True):
                if self.is_file:
                    dpg.add_button(
                        label=LBL_BUTTON_LOAD,
                        tag=TAG_CONVERTER_LOAD_BUTTON,
                        callback=self._on_load_clicked,
                        enabled=False,
                        width=DIM_CONVERTER_BUTTON_WIDTH,
                    )
                    dpg.add_spacer(width=DIM_CONVERTER_BUTTON_SPACING)

                dpg.add_button(
                    label=LBL_BUTTON_CANCEL,
                    tag=TAG_CONVERTER_CANCEL_BUTTON,
                    callback=self._on_cancel_clicked,
                    width=DIM_CONVERTER_BUTTON_WIDTH,
                )

        self.converter.start(self.target_path, self.is_file)

    def _create_path_handler(self) -> str:
        handler_tag = f"{TAG_CONVERTER_PATH_TEXT}{SUF_CONVERTER_HANDLER}"
        if dpg.does_item_exist(handler_tag):
            dpg.delete_item(handler_tag)

        with dpg.item_handler_registry(tag=handler_tag):
            dpg.add_item_clicked_handler(callback=self._on_path_clicked)

        return handler_tag

    def _on_path_clicked(self) -> None:
        pass

    def _on_load_clicked(self) -> None:
        if self.output_file_path and self.on_load_callback:
            self.on_load_callback(self.output_file_path)
        self._on_close()

    def _on_cancel_clicked(self) -> None:
        if self.converter and self.converter.is_running():
            self.converter.cancel()
        self._on_close()

    def _on_close(self) -> None:
        if self.converter and self.converter.is_running():
            self.converter.cancel()
        if dpg.does_item_exist(TAG_CONVERTER_WINDOW):
            dpg.delete_item(TAG_CONVERTER_WINDOW)

    def _on_conversion_complete(self, output_path: Optional[Path]) -> None:
        self.set_completed(output_path)
        self._show_success_dialog()

    def _on_conversion_error(self, error_message: str) -> None:
        self._show_error_dialog(error_message)
        self._on_close()

    def _show_error_dialog(self, error_message: str) -> None:
        def content(parent: str) -> None:
            dpg.add_text(MSG_CONVERTER_ERROR_PREFIX, parent=parent)
            dpg.add_separator(parent=parent)
            dpg.add_text(error_message, wrap=DIM_DIALOG_CONVERTER_WIDTH - 20, parent=parent)

        show_modal_dialog(
            tag=TAG_CONVERTER_ERROR_DIALOG,
            title=TITLE_DIALOG_ERROR,
            content=content,
        )

    def _show_success_dialog(self) -> None:
        def content(parent: str) -> None:
            dpg.add_text(MSG_CONVERTER_SUCCESS, parent=parent)

        show_modal_dialog(
            tag=TAG_CONVERTER_SUCCESS_DIALOG,
            title=TITLE_DIALOG_CONVERTER,
            content=content,
        )

    def update_progress(self, progress: float, current_file: Optional[str] = None) -> None:
        if dpg.does_item_exist(TAG_CONVERTER_PROGRESS):
            dpg.set_value(TAG_CONVERTER_PROGRESS, progress)

        if current_file and dpg.does_item_exist(TAG_CONVERTER_STATUS):
            from constants.browser import MSG_CONVERTER_PROCESSING

            dpg.set_value(TAG_CONVERTER_STATUS, MSG_CONVERTER_PROCESSING.format(current_file))

    def set_completed(self, output_path: Optional[Path] = None) -> None:
        if output_path:
            self.output_file_path = output_path

        if dpg.does_item_exist(TAG_CONVERTER_PROGRESS):
            from constants.browser import VAL_GLOBAL_PROGRESS_COMPLETE

            dpg.set_value(TAG_CONVERTER_PROGRESS, VAL_GLOBAL_PROGRESS_COMPLETE)

        if dpg.does_item_exist(TAG_CONVERTER_STATUS):
            from constants.browser import MSG_CONVERTER_COMPLETED

            dpg.set_value(TAG_CONVERTER_STATUS, MSG_CONVERTER_COMPLETED)

        if self.is_file and dpg.does_item_exist(TAG_CONVERTER_LOAD_BUTTON):
            dpg.configure_item(TAG_CONVERTER_LOAD_BUTTON, enabled=True)
