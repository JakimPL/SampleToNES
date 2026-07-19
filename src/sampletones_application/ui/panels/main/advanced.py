from pathlib import Path
from typing import Any, Callable, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.global_ import StatusElements
from sampletones_application.categories.elements.main import AdvancedElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.general.colors import PathColors
from sampletones_application.tags.general import SUF_HANDLER_REGISTRY
from sampletones_application.tags.main import (
    TAG_MAIN_ADVANCED_BUTTON_SELECT_LIBRARY_DIRECTORY,
    TAG_MAIN_ADVANCED_BUTTON_SELECT_OUTPUT_DIRECTORY,
    TAG_MAIN_ADVANCED_COMBO_SPECTRUM_METHOD,
    TAG_MAIN_ADVANCED_GROUP_LIBRARY_DIRECTORY,
    TAG_MAIN_ADVANCED_GROUP_RECONSTRUCTIONS_DIRECTORY,
    TAG_MAIN_ADVANCED_INPUT_MAX_WORKERS,
    TAG_MAIN_ADVANCED_INPUT_TRANSFORMATION_GAMMA,
    TAG_MAIN_ADVANCED_PANEL,
    TAG_MAIN_ADVANCED_PATH_LIBRARY_DIRECTORY_DISPLAY,
    TAG_MAIN_ADVANCED_PATH_OUTPUT_DIRECTORY_DISPLAY,
)
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.field import labeled_field, subheader
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.elements.path import GUIPathText
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.utils.gui.align import table_wrapper
from sampletones_application.utils.gui.tooltip import show_tooltip
from sampletones_application.utils.gui.widgets import clamp_widget_value
from sampletones_application.view_model.main.advanced import (
    AdvancedSettingsPanelViewModel,
)
from sampletones_application.view_model.main.updates import AdvancedSettingsUpdate
from sampletones_core.configs.display import (
    SPECTRUM_METHOD_BY_LABEL,
    format_spectrum_method,
)
from sampletones_core.constants.algorithm import MAX_TRANSFORMATION_GAMMA
from sampletones_core.constants.enums import SpectrumMethod
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import VoidCallback


class GUIAdvancedSettingsPanel(GUIPanel):
    def __init__(
        self,
        initial_view: AdvancedSettingsPanelViewModel,
        *,
        panel_height: int,
        button_height: int,
        input_width: int,
        label_width: int,
        max_workers_minimum: int,
        language_manager: LanguageManager,
        status_bar: GUIStatusBar,
        path_colors: PathColors,
        initial_collapsed: bool = False,
    ) -> None:
        self.on_advanced_settings_changed: Optional[Callable[[AdvancedSettingsUpdate], None]] = None
        self.on_select_library_directory: Optional[VoidCallback] = None
        self.on_select_output_directory: Optional[VoidCallback] = None
        self.on_update_library_directory: Optional[VoidCallback] = None
        self.on_update_output_directory: Optional[VoidCallback] = None

        self._library_directory: Path = initial_view.library_directory
        self._output_directory: Path = initial_view.reconstructions_directory
        self._max_workers: int = initial_view.max_workers
        self._spectrum_method: SpectrumMethod = initial_view.spectrum_method
        self._transformation_gamma: int = initial_view.transformation_gamma
        self._button_height = button_height
        self._input_width = input_width
        self._label_width = label_width
        self._max_workers_minimum = max_workers_minimum
        self._status_bar = status_bar
        self._path_colors = path_colors
        self._msg_path = language_manager[
            Page.GLOBAL,
            Panel.STATUS,
            TextType.MESSAGE,
            StatusElements.PATH,
        ]

        self._item_handler_tag = f"{TAG_MAIN_ADVANCED_PANEL}{SUF_HANDLER_REGISTRY}"

        self.library_path_text: Optional[GUIPathText] = None
        self.output_path_text: Optional[GUIPathText] = None

        self._lbl_section = language_manager[
            Page.MAIN,
            Panel.ADVANCED,
            TextType.LABEL,
            AdvancedElements.SECTION,
        ]
        self._lbl_select_library = language_manager[
            Page.MAIN,
            Panel.ADVANCED,
            TextType.LABEL,
            AdvancedElements.SELECT_LIBRARY_DIRECTORY,
        ]
        self._lbl_select_output = language_manager[
            Page.MAIN,
            Panel.ADVANCED,
            TextType.LABEL,
            AdvancedElements.SELECT_OUTPUT_DIRECTORY,
        ]
        self._lbl_section_method = language_manager[
            Page.MAIN,
            Panel.ADVANCED,
            TextType.LABEL,
            AdvancedElements.SECTION_METHOD,
        ]
        self._lbl_spectrum_method = language_manager[
            Page.MAIN,
            Panel.ADVANCED,
            TextType.LABEL,
            AdvancedElements.COMBO_SPECTRUM_METHOD,
        ]
        self._lbl_gamma = language_manager[
            Page.MAIN,
            Panel.ADVANCED,
            TextType.LABEL,
            AdvancedElements.SLIDER_TRANSFORMATION_GAMMA,
        ]
        self._lbl_max_workers = language_manager[
            Page.MAIN,
            Panel.ADVANCED,
            TextType.LABEL,
            AdvancedElements.INPUT_MAX_WORKERS,
        ]
        self._tooltip_spectrum_method = language_manager[
            Page.MAIN,
            Panel.ADVANCED,
            TextType.TOOLTIP,
            AdvancedElements.TOOLTIP_SPECTRUM_METHOD,
        ]
        self._tooltip_gamma = language_manager[
            Page.MAIN,
            Panel.ADVANCED,
            TextType.TOOLTIP,
            AdvancedElements.TOOLTIP_TRANSFORMATION_GAMMA,
        ]
        self._tooltip_max_workers = language_manager[
            Page.MAIN,
            Panel.ADVANCED,
            TextType.TOOLTIP,
            AdvancedElements.TOOLTIP_MAX_WORKERS,
        ]
        self._msg_status_combo = language_manager[
            Page.GLOBAL,
            Panel.STATUS,
            TextType.MESSAGE,
            StatusElements.COMBO,
        ]
        self._msg_status_input = language_manager[
            Page.GLOBAL,
            Panel.STATUS,
            TextType.MESSAGE,
            StatusElements.INPUT,
        ]

        super().__init__(
            tag=TAG_MAIN_ADVANCED_PANEL,
            height=panel_height,
        )
        self._enable_vertical_collapse(
            initial_collapsed=initial_collapsed,
        )

    def create_panel(self, parent: str) -> None:
        self._setup_handlers()
        with self._collapsible_card(
            parent,
            self._lbl_section,
            glyph=self._glyphs.headers.advanced,
            width=self.width,
        ):
            self._create_generation_method_settings()
            dpg.add_separator()
            self._create_workers_settings()
            dpg.add_separator()
            self._create_path_settings()
            self._create_tooltips()

    def _setup_handlers(self) -> None:
        with dpg.item_handler_registry(tag=self._item_handler_tag):
            dpg.add_item_deactivated_handler(callback=self._on_parameter_change)
            dpg.add_item_deactivated_after_edit_handler(callback=self._on_parameter_change)
            dpg.add_item_edited_handler(callback=self._on_parameter_change)

    def _on_parameter_change(self, sender: Sender, app_data: Any) -> None:
        self.call(self.on_advanced_settings_changed, self._current_update())

    def _current_update(self) -> AdvancedSettingsUpdate:
        return AdvancedSettingsUpdate(
            max_workers=int(clamp_widget_value(TAG_MAIN_ADVANCED_INPUT_MAX_WORKERS)),
            spectrum_method=self._selected_spectrum_method(),
            transformation_gamma=int(clamp_widget_value(TAG_MAIN_ADVANCED_INPUT_TRANSFORMATION_GAMMA)),
            library_directory=self._library_directory,
            reconstructions_directory=self._output_directory,
        )

    def _selected_spectrum_method(self) -> SpectrumMethod:
        label = dpg.get_value(TAG_MAIN_ADVANCED_COMBO_SPECTRUM_METHOD)
        return SPECTRUM_METHOD_BY_LABEL[label]

    @table_wrapper(columns=2, height=-1)
    def _create_path_settings(self) -> None:
        self._create_library_directory_selection()
        self._create_output_directory_selection()

    def _create_generation_method_settings(self) -> None:
        subheader(self._lbl_section_method)
        with labeled_field(self._lbl_spectrum_method, self._label_width):
            dpg.add_combo(
                tag=TAG_MAIN_ADVANCED_COMBO_SPECTRUM_METHOD,
                items=[format_spectrum_method(method) for method in SpectrumMethod],
                default_value=format_spectrum_method(self._spectrum_method),
                width=self._input_width,
                callback=self._on_parameter_change,
            )
        with labeled_field(self._lbl_gamma, self._label_width):
            input_gamma = dpg.add_slider_int(
                tag=TAG_MAIN_ADVANCED_INPUT_TRANSFORMATION_GAMMA,
                default_value=self._transformation_gamma,
                min_value=0,
                max_value=MAX_TRANSFORMATION_GAMMA,
                width=self._input_width,
                callback=self._on_parameter_change,
            )
            FontRegistry.bind_to_item(input_gamma, Font.MONO)

        dpg.bind_item_handler_registry(
            TAG_MAIN_ADVANCED_INPUT_TRANSFORMATION_GAMMA,
            self._item_handler_tag,
        )
        self._status_bar.bind_to_item(TAG_MAIN_ADVANCED_COMBO_SPECTRUM_METHOD, self._msg_status_combo)
        self._status_bar.bind_to_item(TAG_MAIN_ADVANCED_INPUT_TRANSFORMATION_GAMMA, self._msg_status_input)

    def _create_workers_settings(self) -> None:
        with labeled_field(self._lbl_max_workers, self._label_width):
            input_value = dpg.add_input_int(
                default_value=self._max_workers,
                tag=TAG_MAIN_ADVANCED_INPUT_MAX_WORKERS,
                min_value=self._max_workers_minimum,
                width=self._input_width,
            )
            FontRegistry.bind_to_item(input_value, Font.MONO)

        dpg.bind_item_handler_registry(
            TAG_MAIN_ADVANCED_INPUT_MAX_WORKERS,
            self._item_handler_tag,
        )

    def _create_library_directory_selection(self) -> None:
        with dpg.child_window(
            tag=TAG_MAIN_ADVANCED_GROUP_LIBRARY_DIRECTORY,
            width=-1,
            height=-1,
            border=False,
        ):
            GUIButton(
                tag=TAG_MAIN_ADVANCED_BUTTON_SELECT_LIBRARY_DIRECTORY,
                parent=TAG_MAIN_ADVANCED_GROUP_LIBRARY_DIRECTORY,
                label=self._lbl_select_library,
                width=-1,
                height=self._button_height,
                callback=self._on_select_library_directory,
            )

            self.library_path_text = GUIPathText(
                tag=TAG_MAIN_ADVANCED_PATH_LIBRARY_DIRECTORY_DISPLAY,
                parent=TAG_MAIN_ADVANCED_GROUP_LIBRARY_DIRECTORY,
                path=self._library_directory,
                color=self._path_colors.default,
                hover_color=self._path_colors.hover,
                status_message=self._msg_path,
                font=Font.REGULAR_SMALL,
                status_bar=self._status_bar,
            )

    def _create_output_directory_selection(self) -> None:
        with dpg.child_window(
            tag=TAG_MAIN_ADVANCED_GROUP_RECONSTRUCTIONS_DIRECTORY,
            width=-1,
            height=-1,
            border=False,
        ):
            GUIButton(
                tag=TAG_MAIN_ADVANCED_BUTTON_SELECT_OUTPUT_DIRECTORY,
                label=self._lbl_select_output,
                parent=TAG_MAIN_ADVANCED_GROUP_RECONSTRUCTIONS_DIRECTORY,
                width=-1,
                height=self._button_height,
                callback=self._on_select_output_directory,
            )

            self.output_path_text = GUIPathText(
                tag=TAG_MAIN_ADVANCED_PATH_OUTPUT_DIRECTORY_DISPLAY,
                parent=TAG_MAIN_ADVANCED_GROUP_RECONSTRUCTIONS_DIRECTORY,
                path=self._output_directory,
                color=self._path_colors.default,
                hover_color=self._path_colors.hover,
                status_message=self._msg_path,
                font=Font.REGULAR_SMALL,
                status_bar=self._status_bar,
            )

    def _create_tooltips(self) -> None:
        show_tooltip(
            TAG_MAIN_ADVANCED_COMBO_SPECTRUM_METHOD,
            self._tooltip_spectrum_method,
        )
        show_tooltip(
            TAG_MAIN_ADVANCED_INPUT_TRANSFORMATION_GAMMA,
            self._tooltip_gamma,
        )
        show_tooltip(
            TAG_MAIN_ADVANCED_INPUT_MAX_WORKERS,
            self._tooltip_max_workers,
        )

    def _on_select_library_directory(self) -> None:
        self.call(self.on_select_library_directory)

    def change_library_directory(self, directory_path: Path) -> None:
        self._library_directory = directory_path
        self.call(self.on_advanced_settings_changed, self._current_update())

        if self.library_path_text:
            self.library_path_text.set_path(directory_path)

        self.call(self.on_update_library_directory)

    def _on_select_output_directory(self) -> None:
        self.call(self.on_select_output_directory)

    def change_reconstructions_directory(self, directory_path: Path) -> None:
        self._output_directory = directory_path
        self.call(self.on_advanced_settings_changed, self._current_update())

        if self.output_path_text is not None:
            self.output_path_text.set_path(directory_path)

        self.call(self.on_update_output_directory)

    @property
    def library_directory(self) -> Path:
        return self._library_directory

    @property
    def reconstructions_directory(self) -> Path:
        return self._output_directory

    def update_view(self, view_model: AdvancedSettingsPanelViewModel) -> None:
        self._library_directory = view_model.library_directory
        self._output_directory = view_model.reconstructions_directory
        self._spectrum_method = view_model.spectrum_method
        self._transformation_gamma = view_model.transformation_gamma
        dpg.set_value(TAG_MAIN_ADVANCED_INPUT_MAX_WORKERS, view_model.max_workers)
        dpg.set_value(
            TAG_MAIN_ADVANCED_COMBO_SPECTRUM_METHOD,
            format_spectrum_method(view_model.spectrum_method),
        )
        dpg.set_value(
            TAG_MAIN_ADVANCED_INPUT_TRANSFORMATION_GAMMA,
            view_model.transformation_gamma,
        )

        if self.output_path_text:
            self.output_path_text.set_path(view_model.reconstructions_directory)

        if self.library_path_text:
            self.library_path_text.set_path(view_model.library_directory)
