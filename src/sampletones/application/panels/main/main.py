import dearpygui.dearpygui as dpg

from ...constants.main import (
    DIM_PANEL_HEIGHT_MAIN_CONFIG,
    DIM_PANEL_HEIGHT_MAIN_CONVERTER,
    TAG_PANEL_MAIN,
    TAG_PANEL_MAIN_CONFIG_CELL,
    TAG_PANEL_MAIN_RECONSTRUCTOR_CELL,
    TAG_PANEL_MAIN_SETTINGS,
)
from ...elements.panel import GUIPanel
from ...utils.align import table_wrapper
from .advanced import GUIAdvancedSettingsPanel
from .config import GUIConfigPanel
from .converter import GUIConverterPanel
from .reconstructor import GUIReconstructorPanel


class GUIMainPanel(GUIPanel):
    def __init__(
        self,
        config_panel: GUIConfigPanel,
        reconstructor_panel: GUIReconstructorPanel,
        advanced_settings_panel: GUIAdvancedSettingsPanel,
        converter_panel: GUIConverterPanel,
    ) -> None:
        self.config_panel = config_panel
        self.reconstructor_panel = reconstructor_panel
        self.advanced_settings_panel = advanced_settings_panel
        self.converter_panel = converter_panel

        super().__init__(
            tag=TAG_PANEL_MAIN,
            parent=TAG_PANEL_MAIN_SETTINGS,
        )

    def create_panel(self) -> None:
        with dpg.child_window(
            tag=self.tag,
            parent=self.parent,
            border=False,
        ):
            with dpg.child_window(
                tag=TAG_PANEL_MAIN_SETTINGS,
                parent=self.tag,
                width=-1,
                height=-DIM_PANEL_HEIGHT_MAIN_CONVERTER - 8,
                border=False,
            ):
                self._create_settings()
                self._create_advanced_settings()

            self._create_converter()

    @table_wrapper(columns=2, height=DIM_PANEL_HEIGHT_MAIN_CONFIG)
    def _create_settings(self) -> None:
        with dpg.table_cell(tag=TAG_PANEL_MAIN_CONFIG_CELL):
            self.config_panel.create_panel()
        with dpg.table_cell(tag=TAG_PANEL_MAIN_RECONSTRUCTOR_CELL):
            self.reconstructor_panel.create_panel()

    def _create_advanced_settings(self) -> None:
        self.advanced_settings_panel.create_panel()

    def _create_converter(self) -> None:
        self.converter_panel.create_panel()
