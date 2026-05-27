from typing import Any, Callable, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.config.updates import AudioSettingsUpdate, LibrarySettingsUpdate
from sampletones_application.constants.general import DIM_INPUT_WIDTH, MSG_STATUS_INPUT, SUF_HANDLER_REGISTRY
from sampletones_application.constants.main import (
    DIM_PANEL_HEIGHT_MAIN_CONFIG,
    LBL_CHECKBOX_MAIN_CONFIG_NORMALIZE_AUDIO,
    LBL_CHECKBOX_MAIN_CONFIG_QUANTIZE_AUDIO,
    LBL_INPUT_MAIN_CONFIG_CHANGE_RATE,
    LBL_INPUT_MAIN_CONFIG_SAMPLE_RATE,
    LBL_SECTION_MAIN_CONFIG,
    LBL_SECTION_MAIN_CONFIG_LIBRARY_SETTINGS,
    LBL_SLIDER_MAIN_CONFIG_TRANSFORMATION_GAMMA,
    LBL_TOOLTIP_MAIN_CONFIG_CHANGE_RATE,
    LBL_TOOLTIP_MAIN_CONFIG_NORMALIZE,
    LBL_TOOLTIP_MAIN_CONFIG_QUANTIZE,
    LBL_TOOLTIP_MAIN_CONFIG_SAMPLE_RATE,
    LBL_TOOLTIP_MAIN_TRANSFORMATION_GAMMA,
    TAG_CHECKBOX_MAIN_CONFIG_NORMALIZE,
    TAG_CHECKBOX_MAIN_CONFIG_QUANTIZE,
    TAG_INPUT_MAIN_CONFIG_CHANGE_RATE,
    TAG_INPUT_MAIN_CONFIG_SAMPLE_RATE,
    TAG_INPUT_MAIN_CONFIG_TRANSFORMATION_GAMMA,
    TAG_PANEL_MAIN_CONFIG,
    TAG_PANEL_MAIN_CONFIG_CELL,
)
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.panels.main.config.viewmodel import ConfigPanelViewModel
from sampletones_application.utils.tooltip import show_tooltip
from sampletones_application.utils.widgets import clamp_widget_value
from sampletones_core.constants.audio import MAX_SAMPLE_RATE, MIN_SAMPLE_RATE
from sampletones_core.constants.general import (
    MAX_CHANGE_RATE,
    MAX_TRANSFORMATION_GAMMA,
    MIN_CHANGE_RATE,
)
from sampletones_shared.types.application import Sender


class GUIConfigPanel(GUIPanel):
    def __init__(self, initial_view: ConfigPanelViewModel) -> None:
        self._view = initial_view
        self.on_audio_settings_changed: Optional[Callable[[AudioSettingsUpdate], None]] = None
        self.on_library_settings_changed: Optional[Callable[[LibrarySettingsUpdate], None]] = None
        self._item_handler_tag = f"{TAG_PANEL_MAIN_CONFIG}{SUF_HANDLER_REGISTRY}"
        super().__init__(
            tag=TAG_PANEL_MAIN_CONFIG,
            parent=TAG_PANEL_MAIN_CONFIG_CELL,
            height=DIM_PANEL_HEIGHT_MAIN_CONFIG,
        )

    def create_panel(self) -> None:
        self._setup_handlers()
        with dpg.child_window(
            tag=self.tag,
            parent=self.parent,
            width=self.width,
            height=self.height,
            border=True,
        ):
            self._create_section_text()
            self._create_audio_options()
            self._create_library_settings()
            self._create_tooltips()

    def _setup_handlers(self) -> None:
        with dpg.item_handler_registry(tag=self._item_handler_tag):
            dpg.add_item_deactivated_handler(callback=self._on_parameter_change)
            dpg.add_item_deactivated_after_edit_handler(callback=self._on_parameter_change)
            dpg.add_item_edited_handler(callback=self._on_parameter_change)

    def _on_parameter_change(self, sender: Sender, app_data: Any) -> None:
        audio_update = AudioSettingsUpdate(
            normalize=bool(dpg.get_value(TAG_CHECKBOX_MAIN_CONFIG_NORMALIZE)),
            quantize=bool(dpg.get_value(TAG_CHECKBOX_MAIN_CONFIG_QUANTIZE)),
        )
        library_update = LibrarySettingsUpdate(
            sample_rate=int(clamp_widget_value(TAG_INPUT_MAIN_CONFIG_SAMPLE_RATE)),
            change_rate=int(clamp_widget_value(TAG_INPUT_MAIN_CONFIG_CHANGE_RATE)),
            transformation_gamma=int(clamp_widget_value(TAG_INPUT_MAIN_CONFIG_TRANSFORMATION_GAMMA)),
        )
        self.call(self.on_audio_settings_changed, audio_update)
        self.call(self.on_library_settings_changed, library_update)

    def _create_section_text(self) -> None:
        section_text = dpg.add_text(LBL_SECTION_MAIN_CONFIG)
        FontRegistry.bind_to_item(section_text, Font.BOLD)

    def _create_audio_options(self) -> None:
        dpg.add_separator()
        dpg.add_checkbox(
            label=LBL_CHECKBOX_MAIN_CONFIG_NORMALIZE_AUDIO,
            default_value=self._view.normalize,
            tag=TAG_CHECKBOX_MAIN_CONFIG_NORMALIZE,
            callback=self._on_parameter_change,
        )
        dpg.add_checkbox(
            label=LBL_CHECKBOX_MAIN_CONFIG_QUANTIZE_AUDIO,
            default_value=self._view.quantize,
            tag=TAG_CHECKBOX_MAIN_CONFIG_QUANTIZE,
            callback=self._on_parameter_change,
        )

    def _create_library_settings(self) -> None:
        dpg.add_separator()
        dpg.add_text(LBL_SECTION_MAIN_CONFIG_LIBRARY_SETTINGS)
        dpg.add_input_int(
            label=LBL_INPUT_MAIN_CONFIG_SAMPLE_RATE,
            default_value=self._view.sample_rate,
            tag=TAG_INPUT_MAIN_CONFIG_SAMPLE_RATE,
            min_value=MIN_SAMPLE_RATE,
            max_value=MAX_SAMPLE_RATE,
            width=DIM_INPUT_WIDTH,
            callback=self._on_parameter_change,
        )
        dpg.add_input_int(
            label=LBL_INPUT_MAIN_CONFIG_CHANGE_RATE,
            default_value=self._view.change_rate,
            tag=TAG_INPUT_MAIN_CONFIG_CHANGE_RATE,
            min_value=MIN_CHANGE_RATE,
            max_value=MAX_CHANGE_RATE,
            width=DIM_INPUT_WIDTH,
            callback=self._on_parameter_change,
        )
        dpg.add_slider_int(
            label=LBL_SLIDER_MAIN_CONFIG_TRANSFORMATION_GAMMA,
            tag=TAG_INPUT_MAIN_CONFIG_TRANSFORMATION_GAMMA,
            default_value=self._view.transformation_gamma,
            min_value=0,
            max_value=MAX_TRANSFORMATION_GAMMA,
            width=DIM_INPUT_WIDTH,
        )

        for tag in [
            TAG_INPUT_MAIN_CONFIG_SAMPLE_RATE,
            TAG_INPUT_MAIN_CONFIG_CHANGE_RATE,
            TAG_INPUT_MAIN_CONFIG_TRANSFORMATION_GAMMA,
        ]:
            dpg.bind_item_handler_registry(tag, self._item_handler_tag)

        GUIStatusBar.bind_to_item(TAG_INPUT_MAIN_CONFIG_TRANSFORMATION_GAMMA, MSG_STATUS_INPUT)

    def _create_tooltips(self) -> None:
        show_tooltip(TAG_CHECKBOX_MAIN_CONFIG_NORMALIZE, LBL_TOOLTIP_MAIN_CONFIG_NORMALIZE)
        show_tooltip(TAG_CHECKBOX_MAIN_CONFIG_QUANTIZE, LBL_TOOLTIP_MAIN_CONFIG_QUANTIZE)
        show_tooltip(TAG_INPUT_MAIN_CONFIG_SAMPLE_RATE, LBL_TOOLTIP_MAIN_CONFIG_SAMPLE_RATE)
        show_tooltip(TAG_INPUT_MAIN_CONFIG_CHANGE_RATE, LBL_TOOLTIP_MAIN_CONFIG_CHANGE_RATE)
        show_tooltip(TAG_INPUT_MAIN_CONFIG_TRANSFORMATION_GAMMA, LBL_TOOLTIP_MAIN_TRANSFORMATION_GAMMA)

    def update_view(self, viewmodel: ConfigPanelViewModel) -> None:
        self._view = viewmodel
        dpg.set_value(TAG_CHECKBOX_MAIN_CONFIG_NORMALIZE, viewmodel.normalize)
        dpg.set_value(TAG_CHECKBOX_MAIN_CONFIG_QUANTIZE, viewmodel.quantize)
        dpg.set_value(TAG_INPUT_MAIN_CONFIG_SAMPLE_RATE, viewmodel.sample_rate)
        dpg.set_value(TAG_INPUT_MAIN_CONFIG_CHANGE_RATE, viewmodel.change_rate)
        dpg.set_value(TAG_INPUT_MAIN_CONFIG_TRANSFORMATION_GAMMA, viewmodel.transformation_gamma)
