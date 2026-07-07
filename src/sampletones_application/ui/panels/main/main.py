import dearpygui.dearpygui as dpg

from sampletones_application.constants.general import (
    SUF_PANEL_CENTER,
    TAG_GLOBAL_TAB_MAIN,
    TAG_GLOBAL_THEME_PANEL_SURFACE,
)
from sampletones_application.constants.main import (
    TAG_MAIN_CONFIG_PANEL_CONFIG_CELL,
    TAG_MAIN_PANEL,
    TAG_MAIN_RECONSTRUCTOR_PANEL_RECONSTRUCTOR_CELL,
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
from sampletones_application.ui.themes.registry import ThemeRegistry


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
            tag=TAG_MAIN_PANEL,
            parent=f"{TAG_GLOBAL_TAB_MAIN}{SUF_PANEL_CENTER}",
        )

    def create_panel(self) -> None:
        with dpg.child_window(
            tag=self.tag,
            parent=self.parent,
            border=False,
        ):
            self._create_settings()
            dpg.add_spacer(height=self._layout.panel_gap)
            self._create_advanced_settings()
            dpg.add_spacer(height=self._layout.panel_gap)
            self._create_converter()

        self._bind_card_surfaces()

    def _bind_card_surfaces(self) -> None:
        surface_theme = ThemeRegistry.get(TAG_GLOBAL_THEME_PANEL_SURFACE)
        for panel in (
            self.config_panel,
            self.reconstructor_panel,
            self.advanced_settings_panel,
            self.converter_panel,
        ):
            surface_theme.bind_to_item(panel.tag)

    def _create_settings(self) -> None:
        with dpg.table(
            header_row=False,
            policy=dpg.mvTable_SizingStretchProp,
            resizable=False,
            width=-1,
            height=self._layout.config.height,
        ):
            dpg.add_table_column()
            dpg.add_table_column(width_fixed=True, init_width_or_weight=self._layout.panel_gap)
            dpg.add_table_column()
            with dpg.table_row():
                with dpg.table_cell(tag=TAG_MAIN_CONFIG_PANEL_CONFIG_CELL):
                    self.config_panel.create_panel()
                dpg.add_spacer()
                with dpg.table_cell(tag=TAG_MAIN_RECONSTRUCTOR_PANEL_RECONSTRUCTOR_CELL):
                    self.reconstructor_panel.create_panel()

    def _create_advanced_settings(self) -> None:
        self.advanced_settings_panel.create_panel()

    def _create_converter(self) -> None:
        self.converter_panel.create_panel()
