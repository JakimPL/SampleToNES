from typing import Any, Callable, List, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.global_ import (
    ContextElements,
    StatusElements,
)
from sampletones_application.categories.elements.main import ReconstructorElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.general.inputs import InputsLayout
from sampletones_application.layout.tabs.main.reconstructor import ReconstructorLayout
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
    SUF_HANDLER_REGISTRY,
    TAG_GLOBAL_THEME_CHANNEL_NOISE,
    TAG_GLOBAL_THEME_CHANNEL_PULSE1,
    TAG_GLOBAL_THEME_CHANNEL_PULSE2,
    TAG_GLOBAL_THEME_CHANNEL_TRIANGLE,
)
from sampletones_application.tags.main import (
    PRE_MAIN_RECONSTRUCTOR_GENERATOR,
    TAG_MAIN_RECONSTRUCTOR_PANEL,
    TAG_MAIN_RECONSTRUCTOR_SLIDER_DRIVE,
)
from sampletones_application.ui.elements.field import labeled_field, subheader
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.gui.dpg import dpg_set_value
from sampletones_application.utils.gui.tooltip import show_tooltip
from sampletones_application.utils.gui.widgets import clamp_widget_value
from sampletones_application.view_model.main.reconstructor import (
    ReconstructorPanelViewModel,
)
from sampletones_application.view_model.main.updates import GenerationSettingsUpdate
from sampletones_core.constants.algorithm import MAX_DRIVE
from sampletones_core.constants.enums import GeneratorName
from sampletones_shared.types.application import Sender


class GUIReconstructorPanel(GUIPanel):
    def __init__(
        self,
        initial_view: ReconstructorPanelViewModel,
        *,
        layout: ReconstructorLayout,
        inputs: InputsLayout,
        language_manager: LanguageManager,
        status_bar: GUIStatusBar,
        initial_collapsed: bool = False,
    ) -> None:
        self._view = initial_view
        self._layout = layout
        self._input_width = inputs.default_width
        self._label_width = inputs.label_width
        self._status_bar = status_bar
        self.on_generation_settings_changed: Optional[Callable[[GenerationSettingsUpdate], None]] = None
        self._item_handler_tag = compose_tag(TAG_MAIN_RECONSTRUCTOR_PANEL, SUF_HANDLER_REGISTRY)

        self._lbl_section_settings = language_manager[
            Page.MAIN,
            Panel.RECONSTRUCTOR,
            TextType.LABEL,
            ReconstructorElements.SECTION_SETTINGS,
        ]
        self._lbl_section_generators = language_manager[
            Page.MAIN,
            Panel.RECONSTRUCTOR,
            TextType.LABEL,
            ReconstructorElements.SECTION_GENERATORS,
        ]
        self._lbl_drive = language_manager[
            Page.MAIN,
            Panel.RECONSTRUCTOR,
            TextType.LABEL,
            ReconstructorElements.SLIDER_DRIVE,
        ]
        self._tooltip_drive = language_manager[
            Page.MAIN,
            Panel.RECONSTRUCTOR,
            TextType.TOOLTIP,
            ReconstructorElements.TOOLTIP_DRIVE,
        ]
        self._lbl_triangle = language_manager[
            Page.GLOBAL,
            Panel.CONTEXT,
            TextType.LABEL,
            ContextElements.TRIANGLE,
        ]
        self._lbl_pulse_1 = language_manager[
            Page.GLOBAL,
            Panel.CONTEXT,
            TextType.LABEL,
            ContextElements.PULSE_1,
        ]
        self._lbl_pulse_2 = language_manager[
            Page.GLOBAL,
            Panel.CONTEXT,
            TextType.LABEL,
            ContextElements.PULSE_2,
        ]
        self._lbl_noise = language_manager[
            Page.GLOBAL,
            Panel.CONTEXT,
            TextType.LABEL,
            ContextElements.NOISE,
        ]
        self._msg_status_input = language_manager[
            Page.GLOBAL,
            Panel.STATUS,
            TextType.MESSAGE,
            StatusElements.INPUT,
        ]

        super().__init__(
            tag=TAG_MAIN_RECONSTRUCTOR_PANEL,
            height=layout.height,
        )
        self._enable_vertical_collapse(initial_collapsed=initial_collapsed)

    def create_panel(self, parent: str) -> None:
        self._setup_handlers()
        with self._collapsible_card(
            parent,
            self._lbl_section_settings,
            glyph=self._glyphs.headers.reconstruction,
            width=self.width,
        ):
            self._create_generator_selection()
            dpg.add_separator()
            self._create_drive_slider()
            self._create_tooltips()

    def _setup_handlers(self) -> None:
        with dpg.item_handler_registry(tag=self._item_handler_tag):
            dpg.add_item_deactivated_handler(callback=self._on_parameter_change)
            dpg.add_item_deactivated_after_edit_handler(callback=self._on_parameter_change)
            dpg.add_item_edited_handler(callback=self._on_parameter_change)

    def _create_generator_selection(self) -> None:
        subheader(self._lbl_section_generators)

        with dpg.group():
            for generator, label, theme_tag in self._generator_chips():
                checkbox_tag = self._get_generator_checkbox_tag(generator)
                dpg.add_checkbox(
                    label=label,
                    default_value=generator in self._view.generators,
                    tag=checkbox_tag,
                    callback=self._on_parameter_change,
                )
                ThemeRegistry.get(theme_tag).bind_to_item(checkbox_tag)

    def _generator_chips(self) -> List[Tuple[GeneratorName, str, str]]:
        return [
            (GeneratorName.PULSE1, self._lbl_pulse_1, TAG_GLOBAL_THEME_CHANNEL_PULSE1),
            (GeneratorName.PULSE2, self._lbl_pulse_2, TAG_GLOBAL_THEME_CHANNEL_PULSE2),
            (GeneratorName.TRIANGLE, self._lbl_triangle, TAG_GLOBAL_THEME_CHANNEL_TRIANGLE),
            (GeneratorName.NOISE, self._lbl_noise, TAG_GLOBAL_THEME_CHANNEL_NOISE),
        ]

    def _create_drive_slider(self) -> None:
        with labeled_field(self._lbl_drive, self._label_width):
            dpg.add_slider_float(
                tag=TAG_MAIN_RECONSTRUCTOR_SLIDER_DRIVE,
                min_value=0.0,
                max_value=MAX_DRIVE,
                default_value=self._view.drive,
                width=self._input_width,
                format=self._layout.drive_format,
            )

        dpg.bind_item_handler_registry(
            TAG_MAIN_RECONSTRUCTOR_SLIDER_DRIVE,
            self._item_handler_tag,
        )
        self._status_bar.bind_to_item(
            TAG_MAIN_RECONSTRUCTOR_SLIDER_DRIVE,
            self._msg_status_input,
        )
        FontRegistry.bind_to_item(
            TAG_MAIN_RECONSTRUCTOR_SLIDER_DRIVE,
            Font.MONO,
        )

    def _create_tooltips(self) -> None:
        show_tooltip(TAG_MAIN_RECONSTRUCTOR_SLIDER_DRIVE, self._tooltip_drive)

    def _on_parameter_change(self, sender: Sender, app_data: Any) -> None:
        generators = [
            generator for generator in GeneratorName if dpg.get_value(self._get_generator_checkbox_tag(generator))
        ]
        generation_update = GenerationSettingsUpdate(
            drive=float(clamp_widget_value(TAG_MAIN_RECONSTRUCTOR_SLIDER_DRIVE)),
            generators=generators,
        )
        self.call(self.on_generation_settings_changed, generation_update)

    def update_view(self, view_model: ReconstructorPanelViewModel) -> None:
        self._view = view_model
        dpg.set_value(TAG_MAIN_RECONSTRUCTOR_SLIDER_DRIVE, view_model.drive)
        for generator in GeneratorName:
            dpg_set_value(self._get_generator_checkbox_tag(generator), generator in view_model.generators)

    @staticmethod
    def _get_generator_checkbox_tag(generator: GeneratorName) -> str:
        return compose_tag(PRE_MAIN_RECONSTRUCTOR_GENERATOR, generator.value)
