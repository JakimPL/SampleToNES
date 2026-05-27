from typing import Any, Callable

import dearpygui.dearpygui as dpg

from sampletones_application.prototype.config.constraints import MultiplierConstraints
from sampletones_application.prototype.config.layout import MultiplierLayout
from sampletones_application.prototype.constants.multiplier import (
    TAG_PANEL_PROTOTYPE_MULTIPLIER,
    TAG_SLIDER_PROTOTYPE_MULTIPLIER,
)
from sampletones_application.prototype.text.elements import MultiplierElements
from sampletones_application.text.hierarchy import Page, Panel, TextType
from sampletones_application.text.key import TextKey
from sampletones_application.text.manager import LanguageManager
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_shared.types.application import Sender

_KEY_SECTION = TextKey(Page.PROTOTYPE, Panel.MULTIPLIER, TextType.LABEL, MultiplierElements.SECTION_HEADER)
_KEY_SLIDER = TextKey(Page.PROTOTYPE, Panel.MULTIPLIER, TextType.LABEL, MultiplierElements.SLIDER)


class MultiplierPanel(GUIPanel):
    def __init__(
        self,
        parent: str,
        *,
        lang: LanguageManager,
        layout: MultiplierLayout,
        constraints: MultiplierConstraints,
        on_multiplier_changed: Callable[[int], None],
    ) -> None:
        self._lang = lang
        self._on_multiplier_changed = on_multiplier_changed
        self._slider_width = layout.slider_width
        self._min_value = constraints.min_value
        self._max_value = constraints.max_value
        self._default_value = constraints.default_value
        super().__init__(
            tag=TAG_PANEL_PROTOTYPE_MULTIPLIER,
            parent=parent,
            width=layout.panel_width,
            height=layout.panel_height,
        )

    def create_panel(self) -> None:
        with dpg.child_window(
            tag=self.tag,
            parent=self.parent,
            width=self.width,
            height=self.height,
            border=True,
        ):
            dpg.add_text(self._lang[_KEY_SECTION])
            dpg.add_separator()
            dpg.add_slider_int(
                tag=TAG_SLIDER_PROTOTYPE_MULTIPLIER,
                label=self._lang[_KEY_SLIDER],
                default_value=self._default_value,
                min_value=self._min_value,
                max_value=self._max_value,
                width=self._slider_width,
                callback=self._on_slider_changed,
            )

    def _on_slider_changed(self, sender: Sender, app_data: Any) -> None:
        multiplier: int = dpg.get_value(TAG_SLIDER_PROTOTYPE_MULTIPLIER)
        self._on_multiplier_changed(multiplier)
