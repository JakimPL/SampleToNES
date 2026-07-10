from pathlib import Path
from typing import Optional

import dearpygui.dearpygui as dpg

from sampletones_application.constants.general import (
    SUF_GROUP,
    SUF_HANDLER_REGISTRY,
    SUF_LABEL,
)
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.utils.gui.dpg import dpg_delete_item, dpg_set_value
from sampletones_application.utils.gui.frame import FrameCallbackManager
from sampletones_application.utils.gui.tooltip import show_tooltip
from sampletones_shared.types.application import Color, Sender
from sampletones_shared.types.callback import VoidCallback
from sampletones_shared.types.path import Pathlike
from sampletones_shared.utils.callbacks import CallbackMixin
from sampletones_shared.utils.system.paths import (
    DEFAULT_MAX_FILENAME_DISPLAY,
    open_path_in_explorer,
    shorten_filename,
    shorten_path,
    to_path,
)


class GUIPathText(CallbackMixin):
    def __init__(
        self,
        tag: str,
        path: Optional[Path],
        parent: str,
        color: Color,
        hover_color: Color,
        status_message: str,
        prefix: Optional[str] = None,
        font: Optional[Font] = None,
        use_filename_only: bool = False,
        max_filename_length: int = DEFAULT_MAX_FILENAME_DISPLAY,
        *,
        status_bar: GUIStatusBar,
    ) -> None:
        self.tag = tag
        self._status_bar = status_bar
        self.path = path or Path()
        self._use_filename_only = use_filename_only
        self._max_filename_length = max_filename_length
        self.display_text = self._format_display_text(self.path)
        self.label = prefix

        self.tooltip: Optional[Sender] = None

        self.font = font
        self.color = color
        self.hover_color = hover_color
        self._path_color = color
        self._path_hover_color = hover_color
        self._status_message = status_message

        self.parent = parent
        self.label_tag = f"{tag}{SUF_LABEL}"
        self.handler_tag = f"{tag}{SUF_HANDLER_REGISTRY}"
        self.group_tag = f"{tag}{SUF_GROUP}"

        self.on_path_hovered: Optional[VoidCallback] = None

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

    def _format_display_text(self, path: Path) -> str:
        if self._use_filename_only:
            return shorten_filename(
                path.name,
                max_length=self._max_filename_length,
            )

        return shorten_path(path)

    def _create_handler(self) -> None:
        dpg_delete_item(self.handler_tag)

        with dpg.item_handler_registry(tag=self.handler_tag):
            dpg.add_item_clicked_handler(callback=self._on_clicked)
            dpg.add_item_hover_handler(callback=self._on_hover)

        dpg.bind_item_handler_registry(self.tag, self.handler_tag)

    def _on_hover(self) -> None:
        if dpg.does_item_exist(self.tag):
            if dpg.is_item_hovered(self.tag):
                self._status_bar.set(self._status_message)
                dpg.configure_item(self.tag, color=self.hover_color)
                FrameCallbackManager.set_frame_callback(
                    self._on_hover,
                    2,
                )
            else:
                dpg.configure_item(self.tag, color=self.color)

    def _on_clicked(self) -> None:
        if not self.path.exists():
            return

        open_path_in_explorer(self.path)

    def set_path(self, path: Pathlike, shorten: bool = True) -> None:
        self.path = to_path(path)
        if shorten:
            self.display_text = self._format_display_text(self.path)
        else:
            self.display_text = str(self.path)

        self.color = self._path_color
        self.hover_color = self._path_hover_color
        dpg_set_value(self.tag, self.display_text)
        dpg.configure_item(self.tag, color=self.color)
        if self.tooltip is not None:
            dpg.set_value(self.tooltip, self.path_text)

    def set_status(self, text: str, color: Color) -> None:
        """Displays a non-path status (missing or not applicable) in a muted colour.

        The path is cleared so the row is inert: clicking opens nothing and hovering
        keeps the muted colour rather than the interactive highlight.
        """
        self.path = Path()
        self.display_text = text
        self.color = color
        self.hover_color = color
        dpg_set_value(self.tag, text)
        dpg.configure_item(self.tag, color=color)
        if self.tooltip is not None:
            dpg.set_value(self.tooltip, text)

    def get_path(self) -> Path:
        return self.path

    def destroy(self) -> None:
        dpg_delete_item(self.handler_tag)
        dpg_delete_item(self.tag)
