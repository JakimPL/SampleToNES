from pathlib import Path
from typing import Callable, Optional, Union

import dearpygui.dearpygui as dpg

from configs.config import Config
from constants.browser import (
    DIM_DIALOG_CONVERTER_HEIGHT,
    DIM_DIALOG_CONVERTER_WIDTH,
    LBL_BUTTON_CANCEL,
    LBL_BUTTON_LOAD,
    MSG_CONVERTER_IDLE,
    TAG_CONVERTER_CANCEL_BUTTON,
    TAG_CONVERTER_LOAD_BUTTON,
    TAG_CONVERTER_PATH_TEXT,
    TAG_CONVERTER_PROGRESS,
    TAG_CONVERTER_STATUS,
    TAG_CONVERTER_WINDOW,
    TITLE_DIALOG_CONVERTER,
    VAL_GLOBAL_DEFAULT_FLOAT,
)


class ReconstructionConverter:
    def start(self, target_path: Union[str, Path], config: Config) -> None:
        raise NotImplementedError

    def cancel(self) -> None:
        raise NotImplementedError

    def is_running(self) -> bool:
        raise NotImplementedError

    def get_progress(self) -> float:
        raise NotImplementedError

    def get_current_file(self) -> Optional[str]:
        raise NotImplementedError


class GUIConverterWindow:
    def __init__(self, config: Config, on_load_callback: Optional[Callable[[Path], None]] = None) -> None:
        self.config = config
        self.on_load_callback = on_load_callback
        self.converter: Optional[ReconstructionConverter] = None
        self.target_path: Optional[Path] = None
        self.is_file: bool = False
        self.output_file_path: Optional[Path] = None

    def show(self, target_path: Union[str, Path], is_file: bool = False) -> None:
        self.target_path = Path(target_path)
        self.is_file = is_file
        self.output_file_path = None

        if dpg.does_item_exist(TAG_CONVERTER_WINDOW):
            dpg.delete_item(TAG_CONVERTER_WINDOW)

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
                color=(100, 150, 255),
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
                        width=100,
                    )
                    dpg.add_spacer(width=10)

                dpg.add_button(
                    label=LBL_BUTTON_CANCEL,
                    tag=TAG_CONVERTER_CANCEL_BUTTON,
                    callback=self._on_cancel_clicked,
                    width=-1,
                )

    def _create_path_handler(self) -> str:
        handler_tag = f"{TAG_CONVERTER_PATH_TEXT}_handler"
        if dpg.does_item_exist(handler_tag):
            dpg.delete_item(handler_tag)

        with dpg.item_handler_registry(tag=handler_tag):
            dpg.add_item_clicked_handler(callback=self._on_path_clicked)

        return handler_tag

    def _on_path_clicked(self) -> None:
        pass

    def _on_load_clicked(self) -> None:
        pass

    def _on_cancel_clicked(self) -> None:
        pass

    def _on_close(self) -> None:
        if self.converter and self.converter.is_running():
            self.converter.cancel()
        if dpg.does_item_exist(TAG_CONVERTER_WINDOW):
            dpg.delete_item(TAG_CONVERTER_WINDOW)

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
