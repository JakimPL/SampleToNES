from __future__ import annotations

import traceback
from typing import Dict, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.global_ import DialogElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.key import TextKey
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.general import (
    SUF_BUTTON_COPY,
    SUF_GROUP_TRACEBACK,
    SUF_TEXT,
)
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.themes.default import DefaultTheme
from sampletones_application.ui.themes.theme import Theme
from sampletones_application.ui.themes.trace import TracebackTheme
from sampletones_application.utils.clipboard import copy_to_clipboard


class GUITraceback:
    _REGISTRY: Dict[str, GUITraceback] = {}

    def __init__(
        self,
        parent: str,
        exception: Exception,
        language_manager: Optional[LanguageManager] = None,
        theme: Theme = TracebackTheme(),
        button_theme: Theme = DefaultTheme(),
    ) -> None:
        self._parent = parent
        self._tag = f"{parent}{SUF_GROUP_TRACEBACK}"
        self._text = "".join(
            traceback.format_exception(
                type(exception),
                exception,
                exception.__traceback__,
            ),
        )

        if language_manager is not None:
            self._lbl_copied = language_manager[
                TextKey(
                    Page.GLOBAL,
                    Panel.DIALOG,
                    TextType.LABEL,
                    DialogElements.COPIED,
                )
            ]
        else:
            self._lbl_copied = "Copied!"

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
                height=400,
                width=-1,
            )

            self.theme.bind_to_item(traceback_text_tag)

            GUIButton(
                tag=traceback_copy_tag,
                label="Copy to clipboard",
                callback=lambda: copy_to_clipboard(
                    self._text,
                    "Copy to clipboard",
                    traceback_copy_tag,
                    copied_label=self._lbl_copied,
                ),
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
