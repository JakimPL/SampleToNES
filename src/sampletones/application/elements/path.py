import platform
import subprocess
from pathlib import Path
from typing import Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones.typehints import Pathlike, Sender, VoidCallback
from sampletones.utils import get_directory, shorten_path, to_path
from sampletones.utils.callbacks import CallbackMixin

from ..constants.general import (
    COL_PATH_TEXT,
    COL_PATH_TEXT_HOVER,
    SUF_GROUP,
    SUF_LABEL,
    SUF_PATH_HANDLER,
)
from ..elements.fonts.font import Font
from ..elements.fonts.registry import FontRegistry
from ..utils.callbacks import CallbackQueue
from ..utils.dpg import dpg_delete_item, dpg_set_value
from ..utils.tooltip import show_tooltip


class GUIPathText(CallbackMixin):
    def __init__(
        self,
        tag: str,
        path: Optional[Path],
        parent: str,
        prefix: Optional[str] = None,
        font: Optional[Font] = None,
        color: Tuple[int, int, int] = COL_PATH_TEXT,
        hover_color: Tuple[int, int, int] = COL_PATH_TEXT_HOVER,
    ) -> None:
        self.tag = tag
        self.path = path or Path()
        self.display_text = shorten_path(self.path)
        self.label = prefix

        self.tooltip: Optional[Sender] = None

        self.font = font
        self.color = color
        self.hover_color = hover_color

        self.parent = parent
        self.label_tag = f"{tag}{SUF_LABEL}"
        self.handler_tag = f"{tag}{SUF_PATH_HANDLER}"
        self.group_tag = f"{tag}{SUF_GROUP}"

        self.on_item_hovered: Optional[VoidCallback] = None

        self._create_text()
        self._create_handler()

    def _create_text(self) -> None:
        parent = self.group_tag if self.label is not None else self.parent
        if self.label is not None:
            dpg.add_group(horizontal=True, tag=self.group_tag, parent=self.parent)
            dpg.add_text(self.label, tag=self.label_tag, parent=self.group_tag)

        dpg.add_text(
            self.display_text,
            tag=self.tag,
            parent=parent,
            color=self.color,
        )

        if self.font is not None:
            FontRegistry.bind_to_item(self.label_tag, self.font)
            FontRegistry.bind_to_item(self.tag, self.font)

        self.tooltip = show_tooltip(self.tag, self.path_text)

    @property
    def path_text(self) -> str:
        return str(self.path.absolute())

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
            CallbackQueue.add(self._check_hover_state, priority=True)

    def _check_hover_state(self) -> None:
        if not dpg.does_item_exist(self.tag):
            return

        if dpg.does_item_exist(self.tag):
            if dpg.is_item_hovered(self.tag):
                CallbackQueue.add(self._check_hover_state, priority=True)
                self.call(self.on_item_hovered)
            else:
                dpg.configure_item(self.tag, color=self.color)

    def _on_visible(self) -> None:
        if dpg.does_item_exist(self.tag) and not dpg.is_item_hovered(self.tag):
            dpg.configure_item(self.tag, color=self.color)

    def _on_clicked(self) -> None:
        if not self.path.exists():
            return

        path_to_open = get_directory(self.path)
        path_string = str(path_to_open)

        system = platform.system()
        if system == "Windows":
            subprocess.run(["explorer", path_string], check=False)
        elif system == "Darwin":
            subprocess.run(["open", path_string], check=False)
        else:
            subprocess.run(["xdg-open", path_string], check=False)

    def set_path(self, path: Pathlike, shorten: bool = True) -> None:
        self.path = to_path(path)
        self.display_text = shorten_path(self.path) if shorten else str(self.path)
        dpg_set_value(self.tag, self.display_text)
        if self.tooltip is not None:
            dpg.set_value(self.tooltip, self.path_text)

    def get_path(self) -> Path:
        return self.path

    def destroy(self) -> None:
        dpg_delete_item(self.handler_tag)
        dpg_delete_item(self.tag)
