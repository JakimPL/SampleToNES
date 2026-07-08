from typing import Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.sequencer import SequencerModuleElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.sequencer import (
    TAG_SEQUENCER_GRID_PANEL,
    TAG_SEQUENCER_MODULE_BUTTON_EXPORT,
    TAG_SEQUENCER_MODULE_BUTTON_PROPERTIES,
    TAG_SEQUENCER_MODULE_GROUP_ACTIONS,
)
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.utils.gui.dpg import dpg_configure_item
from sampletones_shared.types.callback import VoidCallback


class GUISequencerActionsPanel(GUIPanel):
    """Whole-song actions rendered under the player in the sequencer's center column."""

    def __init__(self, *, language_manager: LanguageManager) -> None:
        self.on_open_properties: Optional[VoidCallback] = None
        self.on_export_module: Optional[VoidCallback] = None

        self._lbl_properties = language_manager[
            Page.SEQUENCER,
            Panel.MODULE,
            TextType.LABEL,
            SequencerModuleElements.PROPERTIES,
        ]
        self._lbl_export_module = language_manager[
            Page.SEQUENCER,
            Panel.MODULE,
            TextType.LABEL,
            SequencerModuleElements.EXPORT_MODULE,
        ]
        self._lbl_project = language_manager[
            Page.SEQUENCER,
            Panel.MODULE,
            TextType.LABEL,
            SequencerModuleElements.PROJECT_SECTION,
        ]

        super().__init__(
            tag=TAG_SEQUENCER_MODULE_GROUP_ACTIONS,
            parent=TAG_SEQUENCER_GRID_PANEL,
        )

    def create_panel(self) -> None:
        with dpg.child_window(
            tag=self.tag,
            parent=self.parent,
            width=-1,
            auto_resize_y=True,
            border=True,
        ):
            self._create_section_header(self._lbl_project)
            GUIButton(
                tag=TAG_SEQUENCER_MODULE_BUTTON_PROPERTIES,
                label=self._lbl_properties,
                parent=self.tag,
                callback=self._on_properties_clicked,
                width=-1,
            )
            GUIButton(
                tag=TAG_SEQUENCER_MODULE_BUTTON_EXPORT,
                label=self._lbl_export_module,
                parent=self.tag,
                callback=self._on_export_clicked,
                width=-1,
            )

    def set_enabled(self, enabled: bool) -> None:
        dpg_configure_item(TAG_SEQUENCER_MODULE_BUTTON_PROPERTIES, enabled=enabled)
        dpg_configure_item(TAG_SEQUENCER_MODULE_BUTTON_EXPORT, enabled=enabled)

    def _on_properties_clicked(self) -> None:
        self.call(self.on_open_properties)

    def _on_export_clicked(self) -> None:
        self.call(self.on_export_module)
