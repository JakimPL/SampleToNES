import dearpygui.dearpygui as dpg

from sampletones_core.constants.audio import MAX_SAMPLE_RATE, MIN_SAMPLE_RATE
from sampletones_core.constants.general import (
    MAX_CHANGE_RATE,
    MAX_TRANSFORMATION_GAMMA,
    MIN_CHANGE_RATE,
)
from sampletones_core.library import InstructionLibraryKey

from ...config.application.manager import ApplicationConfigManager
from ...config.manager import ConfigManager
from ...constants.general import DIM_INPUT_WIDTH, MSG_STATUS_INPUT
from ...constants.main import (
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
from ...elements.fonts.font import Font
from ...elements.fonts.registry import FontRegistry
from ...elements.settings import GUISettingsPanel
from ...elements.status import GUIStatusBar
from ...utils.dpg import dpg_set_value
from ...utils.tooltip import show_tooltip


class GUIConfigPanel(GUISettingsPanel):
    def __init__(
        self,
        config_manager: ConfigManager,
        application_config_manager: ApplicationConfigManager,
    ):
        super().__init__(
            config_manager=config_manager,
            application_config_manager=application_config_manager,
            config_panel_key="config",
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

    def _create_section_text(self) -> None:
        section_text = dpg.add_text(LBL_SECTION_MAIN_CONFIG)
        FontRegistry.bind_to_item(section_text, Font.BOLD)

    def _create_audio_options(self) -> None:
        dpg.add_separator()
        dpg.add_checkbox(
            label=LBL_CHECKBOX_MAIN_CONFIG_NORMALIZE_AUDIO,
            default_value=self.config_manager.config.general.normalize,
            tag=TAG_CHECKBOX_MAIN_CONFIG_NORMALIZE,
            callback=self._on_parameter_change,
        )
        dpg.add_checkbox(
            label=LBL_CHECKBOX_MAIN_CONFIG_QUANTIZE_AUDIO,
            default_value=self.config_manager.config.general.quantize,
            tag=TAG_CHECKBOX_MAIN_CONFIG_QUANTIZE,
            callback=self._on_parameter_change,
        )

    def _create_library_settings(self) -> None:
        dpg.add_separator()
        dpg.add_text(LBL_SECTION_MAIN_CONFIG_LIBRARY_SETTINGS)
        dpg.add_input_int(
            label=LBL_INPUT_MAIN_CONFIG_SAMPLE_RATE,
            default_value=self.config_manager.config.library.sample_rate,
            tag=TAG_INPUT_MAIN_CONFIG_SAMPLE_RATE,
            min_value=MIN_SAMPLE_RATE,
            max_value=MAX_SAMPLE_RATE,
            width=DIM_INPUT_WIDTH,
            callback=self._on_parameter_change,
        )
        dpg.add_input_int(
            label=LBL_INPUT_MAIN_CONFIG_CHANGE_RATE,
            default_value=self.config_manager.config.library.change_rate,
            tag=TAG_INPUT_MAIN_CONFIG_CHANGE_RATE,
            min_value=MIN_CHANGE_RATE,
            max_value=MAX_CHANGE_RATE,
            width=DIM_INPUT_WIDTH,
            callback=self._on_parameter_change,
        )
        dpg.add_slider_int(
            label=LBL_SLIDER_MAIN_CONFIG_TRANSFORMATION_GAMMA,
            tag=TAG_INPUT_MAIN_CONFIG_TRANSFORMATION_GAMMA,
            default_value=self.config_manager.config.library.transformation_gamma,
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

    def apply_library_config(self, library_key: InstructionLibraryKey) -> None:
        gui_updates = self.config_manager.apply_library_config(library_key)
        for tag, value in gui_updates.items():
            dpg_set_value(tag, value)

    def update_gui_from_config(self) -> None:
        if not self.config_manager.config:
            return

        config = self.config_manager.config
        for tag, info in self.config_manager.config_parameters[self._config_panel_key].items():
            section_name = info.section
            section = getattr(config, section_name)
            if hasattr(section, info.name):
                dpg.set_value(tag, getattr(section, info.name))
