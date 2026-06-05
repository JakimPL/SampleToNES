from typing import Any, Callable, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.global_ import (
    ContextElements,
    StatusElements,
)
from sampletones_application.categories.elements.main import ReconstructorElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.config.updates import GenerationSettingsUpdate
from sampletones_application.constants.general import SUF_HANDLER_REGISTRY
from sampletones_application.constants.main import (
    TAG_MAIN_RECONSTRUCTOR_PANEL,
    TAG_MAIN_RECONSTRUCTOR_PANEL_RECONSTRUCTOR_CELL,
    TAG_MAIN_RECONSTRUCTOR_SLIDER_MIXER,
)
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.utils.dpg import dpg_set_value
from sampletones_application.utils.tooltip import show_tooltip
from sampletones_application.utils.widgets import clamp_widget_value
from sampletones_application.view_model.main.reconstructor import (
    ReconstructorPanelViewModel,
)
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.constants.general import MAX_MIXER
from sampletones_shared.types.application import Sender


class GUIReconstructorPanel(GUIPanel):
    def __init__(
        self,
        initial_view: ReconstructorPanelViewModel,
        *,
        input_width: int,
        panel_height: int,
        language_manager: LanguageManager,
    ) -> None:
        self._view = initial_view
        self._input_width = input_width
        self.on_generation_settings_changed: Optional[Callable[[GenerationSettingsUpdate], None]] = None
        self._item_handler_tag = f"{TAG_MAIN_RECONSTRUCTOR_PANEL}{SUF_HANDLER_REGISTRY}"

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
        self._lbl_mixer = language_manager[
            Page.MAIN,
            Panel.RECONSTRUCTOR,
            TextType.LABEL,
            ReconstructorElements.SLIDER_MIXER,
        ]
        self._tooltip_mixer = language_manager[
            Page.MAIN,
            Panel.RECONSTRUCTOR,
            TextType.TOOLTIP,
            ReconstructorElements.TOOLTIP_MIXER,
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
            parent=TAG_MAIN_RECONSTRUCTOR_PANEL_RECONSTRUCTOR_CELL,
            height=panel_height,
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
            self._create_generator_selection()
            self._create_mixer_slider()
            self._create_tooltips()

    def _setup_handlers(self) -> None:
        with dpg.item_handler_registry(tag=self._item_handler_tag):
            dpg.add_item_deactivated_handler(callback=self._on_parameter_change)
            dpg.add_item_deactivated_after_edit_handler(callback=self._on_parameter_change)
            dpg.add_item_edited_handler(callback=self._on_parameter_change)

    def _create_section_text(self) -> None:
        section_text = dpg.add_text(self._lbl_section_settings)
        FontRegistry.bind_to_item(section_text, Font.BOLD)

    def _create_generator_selection(self) -> None:
        dpg.add_separator()
        dpg.add_text(self._lbl_section_generators)

        dpg.add_checkbox(
            label=self._lbl_pulse_1,
            default_value=GeneratorName.PULSE1 in self._view.generators,
            tag=f"gen_{GeneratorName.PULSE1.value}",
            callback=self._on_parameter_change,
        )
        dpg.add_checkbox(
            label=self._lbl_pulse_2,
            default_value=GeneratorName.PULSE2 in self._view.generators,
            tag=f"gen_{GeneratorName.PULSE2.value}",
            callback=self._on_parameter_change,
        )
        dpg.add_checkbox(
            label=self._lbl_triangle,
            default_value=GeneratorName.TRIANGLE in self._view.generators,
            tag=f"gen_{GeneratorName.TRIANGLE.value}",
            callback=self._on_parameter_change,
        )
        dpg.add_checkbox(
            label=self._lbl_noise,
            default_value=GeneratorName.NOISE in self._view.generators,
            tag=f"gen_{GeneratorName.NOISE.value}",
            callback=self._on_parameter_change,
        )

    def _create_mixer_slider(self) -> None:
        dpg.add_separator()
        dpg.add_slider_float(
            label=self._lbl_mixer,
            tag=TAG_MAIN_RECONSTRUCTOR_SLIDER_MIXER,
            min_value=0.0,
            max_value=MAX_MIXER,
            default_value=self._view.mixer,
            width=self._input_width,
        )

        dpg.bind_item_handler_registry(TAG_MAIN_RECONSTRUCTOR_SLIDER_MIXER, self._item_handler_tag)
        GUIStatusBar.bind_to_item(TAG_MAIN_RECONSTRUCTOR_SLIDER_MIXER, self._msg_status_input)

    def _create_tooltips(self) -> None:
        show_tooltip(TAG_MAIN_RECONSTRUCTOR_SLIDER_MIXER, self._tooltip_mixer)

    def _on_parameter_change(self, sender: Sender, app_data: Any) -> None:
        generators = [generator for generator in GeneratorName if dpg.get_value(f"gen_{generator.value}")]
        generation_update = GenerationSettingsUpdate(
            mixer=float(clamp_widget_value(TAG_MAIN_RECONSTRUCTOR_SLIDER_MIXER)),
            generators=generators,
        )
        self.call(self.on_generation_settings_changed, generation_update)

    def update_view(self, viewmodel: ReconstructorPanelViewModel) -> None:
        self._view = viewmodel
        dpg.set_value(TAG_MAIN_RECONSTRUCTOR_SLIDER_MIXER, viewmodel.mixer)
        for generator in GeneratorName:
            tag = f"gen_{generator.value}"
            dpg_set_value(tag, generator in viewmodel.generators)
