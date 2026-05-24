from typing import Any, Callable

import dearpygui.dearpygui as dpg

from sampletones_application.text.hierarchy import Page, Panel, TextType
from sampletones_application.text.key import TextKey
from sampletones_application.text.manager import LanguageManager
from sampletones_shared.types.application import Sender

from ...elements.panel import GUIPanel
from ..config.constraints import LabelInputConstraints
from ..config.layout import LabelInputLayout
from ..constants.label_input import (
    TAG_INPUT_PROTOTYPE_LABEL,
    TAG_PANEL_PROTOTYPE_LABEL,
    TAG_TEXT_PROTOTYPE_VALIDATION,
)
from ..models.label_input import LabelValidationViewModel
from ..text.elements import LabelInputElements

_KEY_SECTION = TextKey(Page.PROTOTYPE, Panel.LABEL_INPUT, TextType.LABEL, LabelInputElements.SECTION_HEADER)
_KEY_INPUT_HINT = TextKey(Page.PROTOTYPE, Panel.LABEL_INPUT, TextType.HINT, LabelInputElements.INPUT)


class LabelInputPanel(GUIPanel):
    def __init__(
        self,
        parent: str,
        *,
        lang: LanguageManager,
        layout: LabelInputLayout,
        constraints: LabelInputConstraints,
        on_label_changed: Callable[[str], None],
    ) -> None:
        self._lang = lang
        self._on_label_changed = on_label_changed
        self._input_width = layout.input_width
        super().__init__(
            tag=TAG_PANEL_PROTOTYPE_LABEL,
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
            dpg.add_input_text(
                tag=TAG_INPUT_PROTOTYPE_LABEL,
                hint=self._lang[_KEY_INPUT_HINT],
                width=self._input_width,
                callback=self._on_input_changed,
            )
            dpg.add_separator()
            dpg.add_text(tag=TAG_TEXT_PROTOTYPE_VALIDATION, default_value="")

    def update_validation(self, view_model: LabelValidationViewModel) -> None:
        dpg.set_value(TAG_TEXT_PROTOTYPE_VALIDATION, view_model.message if not view_model.is_valid else "")

    def _on_input_changed(self, sender: Sender, app_data: Any) -> None:
        label: str = dpg.get_value(TAG_INPUT_PROTOTYPE_LABEL)
        self._on_label_changed(label)
