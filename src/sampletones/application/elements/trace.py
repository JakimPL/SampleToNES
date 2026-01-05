from __future__ import annotations

import traceback
from typing import Dict

import dearpygui.dearpygui as dpg

from ..constants.general import (
    DIM_DIALOG_HEIGHT_TRACEBACK,
    LBL_BUTTON_TRACEBACK_COPY,
    SUF_BUTTON_COPY,
    SUF_TEXT,
    SUF_TRACEBACK,
)
from ..themes.default import DefaultTheme
from ..themes.theme import Theme
from ..themes.trace import TracebackTheme
from ..utils.clipboard import copy_to_clipboard
from .button import GUIButton


class GUITraceback:
    _REGISTRY: Dict[str, GUITraceback] = {}

    def __init__(
        self,
        parent: str,
        exception: Exception,
        theme: Theme = TracebackTheme(),
        button_theme: Theme = DefaultTheme(),
    ) -> None:
        self._parent = parent
        self._tag = f"{parent}{SUF_TRACEBACK}]"
        self._text = "".join(traceback.format_exception(type(exception), exception, exception.__traceback__))

        self.theme = theme
        traceback_text_tag = f"{self._tag}{SUF_TEXT}"
        traceback_copy_tag = f"{self._tag}{SUF_BUTTON_COPY}"

        with dpg.group(tag=self._tag, parent=parent, show=False):
            dpg.add_input_text(
                tag=traceback_text_tag,
                parent=self._tag,
                default_value=self._text,
                multiline=True,
                readonly=True,
                height=DIM_DIALOG_HEIGHT_TRACEBACK,
                width=-1,
            )

            self.theme.bind_to_item(traceback_text_tag)

            GUIButton(
                tag=traceback_copy_tag,
                label=LBL_BUTTON_TRACEBACK_COPY,
                callback=lambda: copy_to_clipboard(self._text, LBL_BUTTON_TRACEBACK_COPY, traceback_copy_tag),
                width=-1,
                theme=button_theme,
            )

        GUITraceback._REGISTRY[self._tag] = self

    def toggle_visibility(self) -> None:
        self.set_visibility(not self.visible)

    def set_visibility(self, visible: bool) -> None:
        dpg.configure_item(self._tag, show=visible)

    def show(self) -> None:
        self.set_visibility(True)

    def hide(self) -> None:
        self.set_visibility(False)

    @property
    def visible(self) -> bool:
        show: bool = dpg.get_item_configuration(self._tag).get("show", False)
        return show

    @property
    def tag(self) -> str:
        return self._tag
