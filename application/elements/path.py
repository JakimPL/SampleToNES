import platform
import subprocess
from pathlib import Path
from typing import Optional, Tuple, Union

import dearpygui.dearpygui as dpg

from utils import shorten_path

from ..constants import (
    CLR_PATH_TEXT,
    CLR_PATH_TEXT_HOVER,
    SUF_CONVERTER_HANDLER,
    SUF_GROUP,
)
from ..utils.common import dpg_delete_item


class GUIPathText:
    def __init__(
        self,
        tag: str,
        path: Path,
        parent: str,
        prefix: Optional[str] = None,
        color: Tuple[int, int, int] = CLR_PATH_TEXT,
        hover_color: Tuple[int, int, int] = CLR_PATH_TEXT_HOVER,
    ) -> None:
        self.tag = tag
        self.path = path
        self.display_text = shorten_path(self.path)
        self.prefix = prefix

        self.color = color
        self.hover_color = hover_color

        self.parent = parent
        self.handler_tag = f"{tag}{SUF_CONVERTER_HANDLER}"
        self.group_tag = f"{tag}{SUF_GROUP}"

        self._create_text()
        self._create_handler()

    def _create_text(self) -> None:
        parent = self.group_tag if self.prefix is not None else self.parent
        if self.prefix is not None:
            dpg.add_group(horizontal=True, tag=self.group_tag, parent=self.parent)
            dpg.add_text(self.prefix, parent=self.group_tag)

        kwargs = {
            "tag": self.tag,
            "color": self.color,
            "parent": parent,
        }

        dpg.add_text(
            self.display_text,
            **kwargs,
        )

    def _create_handler(self) -> None:
        dpg_delete_item(self.handler_tag)

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
        path_string = str(path_to_open)

        system = platform.system()
        if system == "Windows":
            subprocess.run(["explorer", path_string])
        elif system == "Darwin":
            subprocess.run(["open", path_string])
        else:
            subprocess.run(["xdg-open", path_string])

    def set_path(self, path: Union[str, Path], shorten: bool = True) -> None:
        self.path = Path(path)
        self.display_text = shorten_path(self.path) if shorten else str(self.path)
        if dpg.does_item_exist(self.tag):
            dpg.set_value(self.tag, self.display_text)

    def get_path(self) -> Path:
        return self.path

    def destroy(self) -> None:
        dpg_delete_item(self.handler_tag)
        dpg_delete_item(self.tag)
