from typing import Any, Callable, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.main import ConfigPanelElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.tags.general import SUF_HANDLER_REGISTRY
from sampletones_application.tags.main import (
    TAG_MAIN_CONFIG_CHECKBOX_NORMALIZE,
    TAG_MAIN_CONFIG_CHECKBOX_QUANTIZE,
    TAG_MAIN_CONFIG_INPUT_NES_FREQUENCY,
    TAG_MAIN_CONFIG_INPUT_SAMPLE_RATE,
    TAG_MAIN_CONFIG_PANEL,
)
from sampletones_application.ui.elements.field import labeled_field, subheader
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.utils.gui.tooltip import show_tooltip
from sampletones_application.utils.gui.widgets import clamp_widget_value
from sampletones_application.view_model.main.config import ConfigPanelViewModel
from sampletones_application.view_model.main.updates import (
    AudioSettingsUpdate,
    LibrarySettingsUpdate,
)
from sampletones_core.constants.audio import MAX_SAMPLE_RATE, MIN_SAMPLE_RATE
from sampletones_core.constants.general import MAX_NES_FREQUENCY, MIN_NES_FREQUENCY
from sampletones_shared.types.application import Sender


class GUIConfigPanel(GUIPanel):
    def __init__(
        self,
        initial_view: ConfigPanelViewModel,
        *,
        input_width: int,
        label_width: int,
        panel_height: int,
        language_manager: LanguageManager,
        status_bar: GUIStatusBar,
        initial_collapsed: bool = False,
    ) -> None:
        self._view = initial_view
        self._input_width = input_width
        self._label_width = label_width
        self._status_bar = status_bar
        self.on_audio_settings_changed: Optional[Callable[[AudioSettingsUpdate], None]] = None
        self.on_library_settings_changed: Optional[Callable[[LibrarySettingsUpdate], None]] = None
        self._item_handler_tag = f"{TAG_MAIN_CONFIG_PANEL}{SUF_HANDLER_REGISTRY}"

        self._lbl_section = language_manager[
            Page.MAIN,
            Panel.CONFIG,
            TextType.LABEL,
            ConfigPanelElements.SECTION,
        ]
        self._lbl_section_library = language_manager[
            Page.MAIN,
            Panel.CONFIG,
            TextType.LABEL,
            ConfigPanelElements.SECTION_LIBRARY,
        ]
        self._lbl_normalize = language_manager[
            Page.MAIN,
            Panel.CONFIG,
            TextType.LABEL,
            ConfigPanelElements.CHECKBOX_NORMALIZE,
        ]
        self._lbl_quantize = language_manager[
            Page.MAIN,
            Panel.CONFIG,
            TextType.LABEL,
            ConfigPanelElements.CHECKBOX_QUANTIZE,
        ]
        self._lbl_sample_rate = language_manager[
            Page.MAIN,
            Panel.CONFIG,
            TextType.LABEL,
            ConfigPanelElements.INPUT_SAMPLE_RATE,
        ]
        self._lbl_nes_frequency = language_manager[
            Page.MAIN,
            Panel.CONFIG,
            TextType.LABEL,
            ConfigPanelElements.INPUT_NES_FREQUENCY,
        ]
        self._tooltip_normalize = language_manager[
            Page.MAIN,
            Panel.CONFIG,
            TextType.TOOLTIP,
            ConfigPanelElements.TOOLTIP_NORMALIZE,
        ]
        self._tooltip_quantize = language_manager[
            Page.MAIN,
            Panel.CONFIG,
            TextType.TOOLTIP,
            ConfigPanelElements.TOOLTIP_QUANTIZE,
        ]
        self._tooltip_sample_rate = language_manager[
            Page.MAIN,
            Panel.CONFIG,
            TextType.TOOLTIP,
            ConfigPanelElements.TOOLTIP_SAMPLE_RATE,
        ]
        self._tooltip_nes_frequency = language_manager[
            Page.MAIN,
            Panel.CONFIG,
            TextType.TOOLTIP,
            ConfigPanelElements.TOOLTIP_NES_FREQUENCY,
        ]
        super().__init__(
            tag=TAG_MAIN_CONFIG_PANEL,
            height=panel_height,
        )
        self._enable_vertical_collapse(initial_collapsed=initial_collapsed)

    def create_panel(self, parent: str) -> None:
        self._setup_handlers()
        with self._collapsible_card(
            parent,
            self._lbl_section,
            glyph=self._glyphs.headers.settings,
            width=self.width,
        ):
            self._create_audio_options()
            dpg.add_separator()
            self._create_library_settings()
            self._create_tooltips()

    def _setup_handlers(self) -> None:
        with dpg.item_handler_registry(tag=self._item_handler_tag):
            dpg.add_item_deactivated_handler(callback=self._on_parameter_change)
            dpg.add_item_deactivated_after_edit_handler(callback=self._on_parameter_change)
            dpg.add_item_edited_handler(callback=self._on_parameter_change)

    def _on_parameter_change(self, sender: Sender, app_data: Any) -> None:
        audio_update = AudioSettingsUpdate(
            normalize=bool(dpg.get_value(TAG_MAIN_CONFIG_CHECKBOX_NORMALIZE)),
            quantize=bool(dpg.get_value(TAG_MAIN_CONFIG_CHECKBOX_QUANTIZE)),
        )
        library_update = LibrarySettingsUpdate(
            sample_rate=int(clamp_widget_value(TAG_MAIN_CONFIG_INPUT_SAMPLE_RATE)),
            nes_frequency=int(clamp_widget_value(TAG_MAIN_CONFIG_INPUT_NES_FREQUENCY)),
        )
        self.call(self.on_audio_settings_changed, audio_update)
        self.call(self.on_library_settings_changed, library_update)

    def _create_audio_options(self) -> None:
        dpg.add_checkbox(
            label=self._lbl_normalize,
            default_value=self._view.normalize,
            tag=TAG_MAIN_CONFIG_CHECKBOX_NORMALIZE,
            callback=self._on_parameter_change,
        )
        dpg.add_checkbox(
            label=self._lbl_quantize,
            default_value=self._view.quantize,
            tag=TAG_MAIN_CONFIG_CHECKBOX_QUANTIZE,
            callback=self._on_parameter_change,
        )

    def _create_library_settings(self) -> None:
        subheader(self._lbl_section_library)
        with labeled_field(self._lbl_sample_rate, self._label_width):
            dpg.add_input_int(
                default_value=self._view.sample_rate,
                tag=TAG_MAIN_CONFIG_INPUT_SAMPLE_RATE,
                min_value=MIN_SAMPLE_RATE,
                max_value=MAX_SAMPLE_RATE,
                width=self._input_width,
                callback=self._on_parameter_change,
            )
        with labeled_field(self._lbl_nes_frequency, self._label_width):
            dpg.add_input_int(
                default_value=self._view.nes_frequency,
                tag=TAG_MAIN_CONFIG_INPUT_NES_FREQUENCY,
                min_value=MIN_NES_FREQUENCY,
                max_value=MAX_NES_FREQUENCY,
                width=self._input_width,
                callback=self._on_parameter_change,
            )
        for tag in [
            TAG_MAIN_CONFIG_INPUT_SAMPLE_RATE,
            TAG_MAIN_CONFIG_INPUT_NES_FREQUENCY,
        ]:
            dpg.bind_item_handler_registry(tag, self._item_handler_tag)
            FontRegistry.bind_to_item(tag, Font.MONO)

    def _create_tooltips(self) -> None:
        show_tooltip(TAG_MAIN_CONFIG_CHECKBOX_NORMALIZE, self._tooltip_normalize)
        show_tooltip(TAG_MAIN_CONFIG_CHECKBOX_QUANTIZE, self._tooltip_quantize)
        show_tooltip(TAG_MAIN_CONFIG_INPUT_SAMPLE_RATE, self._tooltip_sample_rate)
        show_tooltip(TAG_MAIN_CONFIG_INPUT_NES_FREQUENCY, self._tooltip_nes_frequency)

    def update_view(self, view_model: ConfigPanelViewModel) -> None:
        self._view = view_model
        dpg.set_value(TAG_MAIN_CONFIG_CHECKBOX_NORMALIZE, view_model.normalize)
        dpg.set_value(TAG_MAIN_CONFIG_CHECKBOX_QUANTIZE, view_model.quantize)
        dpg.set_value(TAG_MAIN_CONFIG_INPUT_SAMPLE_RATE, view_model.sample_rate)
        dpg.set_value(TAG_MAIN_CONFIG_INPUT_NES_FREQUENCY, view_model.nes_frequency)
