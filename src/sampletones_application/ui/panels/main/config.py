from typing import Any, Callable, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.global_ import StatusElements
from sampletones_application.categories.elements.main import ConfigPanelElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.general import SUF_HANDLER_REGISTRY
from sampletones_application.constants.main import (
    TAG_MAIN_CONFIG_CHECKBOX_NORMALIZE,
    TAG_MAIN_CONFIG_CHECKBOX_QUANTIZE,
    TAG_MAIN_CONFIG_COMBO_SPECTRUM_METHOD,
    TAG_MAIN_CONFIG_INPUT_NES_FREQUENCY,
    TAG_MAIN_CONFIG_INPUT_SAMPLE_RATE,
    TAG_MAIN_CONFIG_INPUT_TRANSFORMATION_GAMMA,
    TAG_MAIN_CONFIG_PANEL,
)
from sampletones_application.ui.elements.layout.card import card
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.utils.gui.tooltip import show_tooltip
from sampletones_application.utils.gui.widgets import clamp_widget_value
from sampletones_application.view_model.main.config import ConfigPanelViewModel
from sampletones_application.view_model.main.updates import (
    AudioSettingsUpdate,
    LibrarySettingsUpdate,
)
from sampletones_core.configs.display import (
    SPECTRUM_METHOD_BY_LABEL,
    format_spectrum_method,
)
from sampletones_core.constants.algorithm import MAX_TRANSFORMATION_GAMMA
from sampletones_core.constants.audio import MAX_SAMPLE_RATE, MIN_SAMPLE_RATE
from sampletones_core.constants.enums import SpectrumMethod
from sampletones_core.constants.general import MAX_NES_FREQUENCY, MIN_NES_FREQUENCY
from sampletones_shared.types.application import Sender


class GUIConfigPanel(GUIPanel):
    def __init__(
        self,
        initial_view: ConfigPanelViewModel,
        *,
        input_width: int,
        panel_height: int,
        language_manager: LanguageManager,
        status_bar: GUIStatusBar,
    ) -> None:
        self._view = initial_view
        self._input_width = input_width
        self._status_bar = status_bar
        self.on_audio_settings_changed: Optional[Callable[[AudioSettingsUpdate], None]] = None
        self.on_library_settings_changed: Optional[Callable[[LibrarySettingsUpdate], None]] = None
        self._item_handler_tag = f"{TAG_MAIN_CONFIG_PANEL}{SUF_HANDLER_REGISTRY}"

        self._lbl_section = language_manager[
            Page.MAIN,
            Panel.CONFIG_PANEL,
            TextType.LABEL,
            ConfigPanelElements.SECTION,
        ]
        self._lbl_section_library = language_manager[
            Page.MAIN,
            Panel.CONFIG_PANEL,
            TextType.LABEL,
            ConfigPanelElements.SECTION_LIBRARY,
        ]
        self._lbl_normalize = language_manager[
            Page.MAIN,
            Panel.CONFIG_PANEL,
            TextType.LABEL,
            ConfigPanelElements.CHECKBOX_NORMALIZE,
        ]
        self._lbl_quantize = language_manager[
            Page.MAIN,
            Panel.CONFIG_PANEL,
            TextType.LABEL,
            ConfigPanelElements.CHECKBOX_QUANTIZE,
        ]
        self._lbl_sample_rate = language_manager[
            Page.MAIN,
            Panel.CONFIG_PANEL,
            TextType.LABEL,
            ConfigPanelElements.INPUT_SAMPLE_RATE,
        ]
        self._lbl_nes_frequency = language_manager[
            Page.MAIN,
            Panel.CONFIG_PANEL,
            TextType.LABEL,
            ConfigPanelElements.INPUT_NES_FREQUENCY,
        ]
        self._lbl_spectrum_method = language_manager[
            Page.MAIN,
            Panel.CONFIG_PANEL,
            TextType.LABEL,
            ConfigPanelElements.COMBO_SPECTRUM_METHOD,
        ]
        self._lbl_gamma = language_manager[
            Page.MAIN,
            Panel.CONFIG_PANEL,
            TextType.LABEL,
            ConfigPanelElements.SLIDER_TRANSFORMATION_GAMMA,
        ]
        self._tooltip_normalize = language_manager[
            Page.MAIN,
            Panel.CONFIG_PANEL,
            TextType.TOOLTIP,
            ConfigPanelElements.TOOLTIP_NORMALIZE,
        ]
        self._tooltip_quantize = language_manager[
            Page.MAIN,
            Panel.CONFIG_PANEL,
            TextType.TOOLTIP,
            ConfigPanelElements.TOOLTIP_QUANTIZE,
        ]
        self._tooltip_sample_rate = language_manager[
            Page.MAIN,
            Panel.CONFIG_PANEL,
            TextType.TOOLTIP,
            ConfigPanelElements.TOOLTIP_SAMPLE_RATE,
        ]
        self._tooltip_nes_frequency = language_manager[
            Page.MAIN,
            Panel.CONFIG_PANEL,
            TextType.TOOLTIP,
            ConfigPanelElements.TOOLTIP_NES_FREQUENCY,
        ]
        self._tooltip_spectrum_method = language_manager[
            Page.MAIN,
            Panel.CONFIG_PANEL,
            TextType.TOOLTIP,
            ConfigPanelElements.TOOLTIP_SPECTRUM_METHOD,
        ]
        self._tooltip_gamma = language_manager[
            Page.MAIN,
            Panel.CONFIG_PANEL,
            TextType.TOOLTIP,
            ConfigPanelElements.TOOLTIP_TRANSFORMATION_GAMMA,
        ]
        self._msg_status_input = language_manager[
            Page.GLOBAL,
            Panel.STATUS,
            TextType.MESSAGE,
            StatusElements.INPUT,
        ]
        self._msg_status_combo = language_manager[
            Page.GLOBAL,
            Panel.STATUS,
            TextType.MESSAGE,
            StatusElements.COMBO,
        ]

        super().__init__(
            tag=TAG_MAIN_CONFIG_PANEL,
            height=panel_height,
        )

    def create_panel(self, parent: str) -> None:
        self._setup_handlers()
        with card(parent, self.tag, width=self.width, height=self.height, auto_resize_y=False):
            self._create_section_text()
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
            spectrum_method=self._selected_spectrum_method(),
            transformation_gamma=int(clamp_widget_value(TAG_MAIN_CONFIG_INPUT_TRANSFORMATION_GAMMA)),
        )
        self.call(self.on_audio_settings_changed, audio_update)
        self.call(self.on_library_settings_changed, library_update)

    def _selected_spectrum_method(self) -> SpectrumMethod:
        label = dpg.get_value(TAG_MAIN_CONFIG_COMBO_SPECTRUM_METHOD)
        return SPECTRUM_METHOD_BY_LABEL[label]

    def _create_section_text(self) -> None:
        self._create_section_header(
            self._lbl_section,
            glyph=self._glyphs.headers.settings,
        )

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
        dpg.add_text(self._lbl_section_library)
        dpg.add_input_int(
            label=self._lbl_sample_rate,
            default_value=self._view.sample_rate,
            tag=TAG_MAIN_CONFIG_INPUT_SAMPLE_RATE,
            min_value=MIN_SAMPLE_RATE,
            max_value=MAX_SAMPLE_RATE,
            width=self._input_width,
            callback=self._on_parameter_change,
        )
        dpg.add_input_int(
            label=self._lbl_nes_frequency,
            default_value=self._view.nes_frequency,
            tag=TAG_MAIN_CONFIG_INPUT_NES_FREQUENCY,
            min_value=MIN_NES_FREQUENCY,
            max_value=MAX_NES_FREQUENCY,
            width=self._input_width,
            callback=self._on_parameter_change,
        )
        dpg.add_combo(
            label=self._lbl_spectrum_method,
            tag=TAG_MAIN_CONFIG_COMBO_SPECTRUM_METHOD,
            items=[format_spectrum_method(method) for method in SpectrumMethod],
            default_value=format_spectrum_method(self._view.spectrum_method),
            width=self._input_width,
            callback=self._on_parameter_change,
        )
        dpg.add_slider_int(
            label=self._lbl_gamma,
            tag=TAG_MAIN_CONFIG_INPUT_TRANSFORMATION_GAMMA,
            default_value=self._view.transformation_gamma,
            min_value=0,
            max_value=MAX_TRANSFORMATION_GAMMA,
            width=self._input_width,
            callback=self._on_parameter_change,
        )

        for tag in [
            TAG_MAIN_CONFIG_INPUT_SAMPLE_RATE,
            TAG_MAIN_CONFIG_INPUT_NES_FREQUENCY,
            TAG_MAIN_CONFIG_INPUT_TRANSFORMATION_GAMMA,
        ]:
            dpg.bind_item_handler_registry(tag, self._item_handler_tag)

        self._status_bar.bind_to_item(TAG_MAIN_CONFIG_COMBO_SPECTRUM_METHOD, self._msg_status_combo)
        self._status_bar.bind_to_item(TAG_MAIN_CONFIG_INPUT_TRANSFORMATION_GAMMA, self._msg_status_input)

    def _create_tooltips(self) -> None:
        show_tooltip(TAG_MAIN_CONFIG_CHECKBOX_NORMALIZE, self._tooltip_normalize)
        show_tooltip(TAG_MAIN_CONFIG_CHECKBOX_QUANTIZE, self._tooltip_quantize)
        show_tooltip(TAG_MAIN_CONFIG_INPUT_SAMPLE_RATE, self._tooltip_sample_rate)
        show_tooltip(TAG_MAIN_CONFIG_INPUT_NES_FREQUENCY, self._tooltip_nes_frequency)
        show_tooltip(TAG_MAIN_CONFIG_COMBO_SPECTRUM_METHOD, self._tooltip_spectrum_method)
        show_tooltip(TAG_MAIN_CONFIG_INPUT_TRANSFORMATION_GAMMA, self._tooltip_gamma)

    def update_view(self, view_model: ConfigPanelViewModel) -> None:
        self._view = view_model
        dpg.set_value(TAG_MAIN_CONFIG_CHECKBOX_NORMALIZE, view_model.normalize)
        dpg.set_value(TAG_MAIN_CONFIG_CHECKBOX_QUANTIZE, view_model.quantize)
        dpg.set_value(TAG_MAIN_CONFIG_INPUT_SAMPLE_RATE, view_model.sample_rate)
        dpg.set_value(TAG_MAIN_CONFIG_INPUT_NES_FREQUENCY, view_model.nes_frequency)
        dpg.set_value(
            TAG_MAIN_CONFIG_COMBO_SPECTRUM_METHOD,
            format_spectrum_method(view_model.spectrum_method),
        )
        dpg.set_value(
            TAG_MAIN_CONFIG_INPUT_TRANSFORMATION_GAMMA,
            view_model.transformation_gamma,
        )
