import platform
import subprocess
from pathlib import Path
from typing import Optional, Tuple, Union

import dearpygui.dearpygui as dpg

from constants.browser import CLR_PATH_TEXT, CLR_PATH_TEXT_HOVER, SUF_CONVERTER_HANDLER


class GUIPathText:
    def __init__(
        self,
        tag: str,
        path: Path,
        parent: Optional[str] = None,
        display_text: Optional[str] = None,
        color: Tuple[int, int, int] = CLR_PATH_TEXT,
        hover_color: Tuple[int, int, int] = CLR_PATH_TEXT_HOVER,
    ) -> None:
        self.tag = tag
        self.path = Path(path)
        self.display_text = display_text if display_text is not None else str(self.path)
        self.color = color
        self.hover_color = hover_color
        self.handler_tag = f"{tag}{SUF_CONVERTER_HANDLER}"

        self._create_text(parent)
        self._create_handler()

    def _create_text(self, parent: Optional[str]) -> None:
        kwargs = {
            "tag": self.tag,
            "color": self.color,
            "parent": parent if parent is not None else 0,
        }

        dpg.add_text(
            self.display_text,
            **kwargs,
        )

    def _create_handler(self) -> None:
        if dpg.does_item_exist(self.handler_tag):
            dpg.delete_item(self.handler_tag)

        with dpg.item_handler_registry(tag=self.handler_tag):
            dpg.add_item_clicked_handler(callback=self._on_clicked)
            dpg.add_item_hover_handler(callback=self._on_hover_start)
            dpg.add_item_visible_handler(callback=self._on_visible)

        dpg.bind_item_handler_registry(self.tag, self.handler_tag)

    def _on_hover_start(self) -> None:
        if dpg.does_item_exist(self.tag):
            dpg.configure_item(self.tag, color=self.hover_color)
            dpg.set_frame_callback(dpg.get_frame_count() + 1, self._check_hover_state)

    def _check_hover_state(self) -> None:
        if not dpg.does_item_exist(self.tag):
            return

        if dpg.is_item_hovered(self.tag):
            dpg.set_frame_callback(dpg.get_frame_count() + 1, self._check_hover_state)
        else:
            dpg.configure_item(self.tag, color=self.color)

    def _on_visible(self) -> None:
        if dpg.does_item_exist(self.tag) and not dpg.is_item_hovered(self.tag):
            dpg.configure_item(self.tag, color=self.color)

    def _on_clicked(self) -> None:
        if not self.path.exists():
            return

        path_to_open = self.path if self.path.is_dir() else self.path.parent

        system = platform.system()
        if system == "Windows":
            subprocess.run(["explorer", str(path_to_open)])
        elif system == "Darwin":
            subprocess.run(["open", str(path_to_open)])
        else:
            subprocess.run(["xdg-open", str(path_to_open)])

    def set_path(self, path: Union[str, Path], display_text: Optional[str] = None) -> None:
        self.path = Path(path)
        self.display_text = display_text if display_text is not None else str(self.path)
        if dpg.does_item_exist(self.tag):
            dpg.set_value(self.tag, self.display_text)

    def get_path(self) -> Path:
        return self.path

    def destroy(self) -> None:
        if dpg.does_item_exist(self.handler_tag):
            dpg.delete_item(self.handler_tag)
        if dpg.does_item_exist(self.tag):
            dpg.delete_item(self.tag)
