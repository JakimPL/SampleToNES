from typing import Callable, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.global_ import StatusElements
from sampletones_application.categories.elements.sequencer import SequencerModuleElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.general import (
    SUF_PANEL_RIGHT,
    TAG_GLOBAL_TAB_SEQUENCER,
)
from sampletones_application.constants.sequencer import (
    TAG_SEQUENCER_MODULE_BUTTON_EXPORT,
    TAG_SEQUENCER_MODULE_GROUP_OPTIONS,
    TAG_SEQUENCER_MODULE_INPUT_NES_FREQUENCY,
    TAG_SEQUENCER_MODULE_INPUT_ROWS,
    TAG_SEQUENCER_MODULE_INPUT_SPEED,
    TAG_SEQUENCER_MODULE_INPUT_TEMPO,
    TAG_SEQUENCER_MODULE_PANEL,
)
from sampletones_application.layout.sequencer import SequencerLayout
from sampletones_application.logic.sequencer.grid import SequencerGridLogic
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.utils.dpg import dpg_configure_item
from sampletones_application.utils.tooltip import show_tooltip
from sampletones_application.utils.widgets import clamp_widget_value
from sampletones_application.view_model.sequencer.settings import SequencerSettingsViewModel
from sampletones_core.constants.general import MAX_NES_FREQUENCY, MIN_NES_FREQUENCY
from sampletones_shared.constants.project import MAX_ROWS_PER_PATTERN, MIN_ROWS_PER_PATTERN
from sampletones_shared.types.application import Sender


class GUISequencerModulePanel(GUIPanel):
    def __init__(
        self,
        sequencer_grid_logic: SequencerGridLogic,
        *,
        layout: SequencerLayout,
        input_width: int,
        language_manager: LanguageManager,
    ) -> None:
        self._sequencer_grid_logic = sequencer_grid_logic
        self._layout = layout
        self._input_width = input_width

        self.on_nes_frequency: Optional[Callable[[int], None]] = None
        self.on_rows_per_pattern: Optional[Callable[[int], None]] = None
        self.on_tempo: Optional[Callable[[int], None]] = None
        self.on_speed: Optional[Callable[[int], None]] = None

        self._lbl_module_options = language_manager[
            Page.SEQUENCER,
            Panel.MODULE,
            TextType.LABEL,
            SequencerModuleElements.MODULE_OPTIONS,
        ]
        self._lbl_nes_frequency = language_manager[
            Page.SEQUENCER,
            Panel.MODULE,
            TextType.LABEL,
            SequencerModuleElements.NES_FREQUENCY,
        ]
        self._lbl_rows = language_manager[
            Page.SEQUENCER,
            Panel.MODULE,
            TextType.LABEL,
            SequencerModuleElements.ROWS,
        ]
        self._tpl_rows_tooltip = language_manager[
            Page.SEQUENCER,
            Panel.MODULE,
            TextType.TOOLTIP,
            SequencerModuleElements.ROWS,
        ]
        self._lbl_tempo = language_manager[
            Page.SEQUENCER,
            Panel.MODULE,
            TextType.LABEL,
            SequencerModuleElements.TEMPO,
        ]
        self._lbl_speed = language_manager[
            Page.SEQUENCER,
            Panel.MODULE,
            TextType.LABEL,
            SequencerModuleElements.SPEED,
        ]
        self._lbl_export_module = language_manager[
            Page.SEQUENCER,
            Panel.MODULE,
            TextType.LABEL,
            SequencerModuleElements.EXPORT_MODULE,
        ]
        self._msg_status_input = language_manager[
            Page.GLOBAL,
            Panel.STATUS,
            TextType.MESSAGE,
            StatusElements.INPUT,
        ]

        super().__init__(
            tag=TAG_SEQUENCER_MODULE_PANEL,
            parent=f"{TAG_GLOBAL_TAB_SEQUENCER}{SUF_PANEL_RIGHT}",
        )

    def create_panel(self) -> None:
        with dpg.group(
            tag=self.tag,
            parent=self.parent,
        ):
            self._create_module_options()
            self._create_export_button()

    def _create_module_options(self) -> None:
        section_text = dpg.add_text(self._lbl_module_options)
        FontRegistry.bind_to_item(section_text, Font.BOLD)
        dpg.add_separator()

        settings = self._sequencer_grid_logic.settings
        with dpg.group(tag=TAG_SEQUENCER_MODULE_GROUP_OPTIONS):
            dpg.add_input_int(
                label=self._lbl_nes_frequency,
                default_value=settings.nes_frequency,
                tag=TAG_SEQUENCER_MODULE_INPUT_NES_FREQUENCY,
                min_value=MIN_NES_FREQUENCY,
                max_value=MAX_NES_FREQUENCY,
                width=self._input_width,
                callback=self._on_nes_frequency_input,
            )
            dpg.add_input_int(
                label=self._lbl_rows,
                default_value=settings.rows_per_pattern,
                tag=TAG_SEQUENCER_MODULE_INPUT_ROWS,
                min_value=MIN_ROWS_PER_PATTERN,
                max_value=MAX_ROWS_PER_PATTERN,
                width=self._input_width,
                on_enter=True,
                callback=self._on_rows_per_pattern_input,
            )
            dpg.add_input_int(
                label=self._lbl_tempo,
                default_value=settings.tempo,
                tag=TAG_SEQUENCER_MODULE_INPUT_TEMPO,
                min_value=self._layout.tempo.min,
                max_value=self._layout.tempo.max,
                width=self._input_width,
                callback=self._on_tempo_input,
            )
            dpg.add_input_int(
                label=self._lbl_speed,
                default_value=settings.speed,
                tag=TAG_SEQUENCER_MODULE_INPUT_SPEED,
                min_value=self._layout.speed.min,
                max_value=self._layout.speed.max,
                width=self._input_width,
                callback=self._on_speed_input,
            )

        show_tooltip(TAG_SEQUENCER_MODULE_INPUT_ROWS, self._tpl_rows_tooltip)
        GUIStatusBar.bind_to_item(TAG_SEQUENCER_MODULE_INPUT_NES_FREQUENCY, self._msg_status_input)
        GUIStatusBar.bind_to_item(TAG_SEQUENCER_MODULE_INPUT_ROWS, self._msg_status_input)
        GUIStatusBar.bind_to_item(TAG_SEQUENCER_MODULE_INPUT_TEMPO, self._msg_status_input)
        GUIStatusBar.bind_to_item(TAG_SEQUENCER_MODULE_INPUT_SPEED, self._msg_status_input)

    def _create_export_button(self) -> None:
        dpg.add_separator()
        GUIButton(
            tag=TAG_SEQUENCER_MODULE_BUTTON_EXPORT,
            label=self._lbl_export_module,
            width=-1,
            font=Font.BOLD,
        )

    def update_settings(self, view_model: SequencerSettingsViewModel) -> None:
        dpg.set_value(TAG_SEQUENCER_MODULE_INPUT_NES_FREQUENCY, view_model.nes_frequency)
        dpg.set_value(TAG_SEQUENCER_MODULE_INPUT_ROWS, view_model.rows_per_pattern)
        dpg.set_value(TAG_SEQUENCER_MODULE_INPUT_TEMPO, view_model.tempo)
        dpg.set_value(TAG_SEQUENCER_MODULE_INPUT_SPEED, view_model.speed)

    def set_enabled(self, enabled: bool) -> None:
        dpg_configure_item(TAG_SEQUENCER_MODULE_GROUP_OPTIONS, enabled=enabled)

    def _on_nes_frequency_input(self, sender: Sender, app_data: int) -> None:
        self.call(self.on_nes_frequency, int(clamp_widget_value(TAG_SEQUENCER_MODULE_INPUT_NES_FREQUENCY)))

    def _on_rows_per_pattern_input(self, sender: Sender, app_data: int) -> None:
        self.call(self.on_rows_per_pattern, int(clamp_widget_value(TAG_SEQUENCER_MODULE_INPUT_ROWS)))

    def _on_tempo_input(self, sender: Sender, app_data: int) -> None:
        self.call(self.on_tempo, int(clamp_widget_value(TAG_SEQUENCER_MODULE_INPUT_TEMPO)))

    def _on_speed_input(self, sender: Sender, app_data: int) -> None:
        self.call(self.on_speed, int(clamp_widget_value(TAG_SEQUENCER_MODULE_INPUT_SPEED)))
