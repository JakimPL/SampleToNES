import dearpygui.dearpygui as dpg

from sampletones_application.constants.main import (
    TAG_PANEL_MAIN,
    TAG_PANEL_MAIN_CONFIG_CELL,
    TAG_PANEL_MAIN_RECONSTRUCTOR_CELL,
    TAG_PANEL_MAIN_SETTINGS,
)
from sampletones_application.layout.main import MainLayout
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.panels.main.advanced import (
    GUIAdvancedSettingsPanel,
)
from sampletones_application.ui.panels.main.config import GUIConfigPanel
from sampletones_application.ui.panels.main.converter.converter import (
    GUIConverterPanel,
)
from sampletones_application.ui.panels.main.reconstructor import (
    GUIReconstructorPanel,
)


class GUIMainPanel(GUIPanel):
    def __init__(
        self,
        config_panel: GUIConfigPanel,
        reconstructor_panel: GUIReconstructorPanel,
        advanced_settings_panel: GUIAdvancedSettingsPanel,
        converter_panel: GUIConverterPanel,
        *,
        layout: MainLayout,
    ) -> None:
        self.config_panel = config_panel
        self.reconstructor_panel = reconstructor_panel
        self.advanced_settings_panel = advanced_settings_panel
        self.converter_panel = converter_panel
        self._layout = layout

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
                height=-self._layout.converter.height - 8,
                border=False,
            ):
                self._create_settings()
                self._create_advanced_settings()

            self._create_converter()

    def _create_settings(self) -> None:
        with dpg.table(
            header_row=False,
            policy=dpg.mvTable_SizingStretchSame,
            resizable=False,
            width=-1,
            height=self._layout.config.height,
        ):
            dpg.add_table_column()
            dpg.add_table_column()
            with dpg.table_row():
                with dpg.table_cell(tag=TAG_PANEL_MAIN_CONFIG_CELL):
                    self.config_panel.create_panel()
                with dpg.table_cell(tag=TAG_PANEL_MAIN_RECONSTRUCTOR_CELL):
                    self.reconstructor_panel.create_panel()

    def _create_advanced_settings(self) -> None:
        self.advanced_settings_panel.create_panel()

    def _create_converter(self) -> None:
        self.converter_panel.create_panel()
