import dearpygui.dearpygui as dpg

from ...constants import (
    DIM_PANEL_CONVERTER_HEIGHT,
    SUF_CENTER_PANEL,
    TAG_PANEL_MAIN,
    TAG_PANEL_MAIN_CONFIG_CELL,
    TAG_PANEL_MAIN_RECONSTRUCTOR_CELL,
    TAG_PANEL_MAIN_SETTINGS,
    TAG_TAB_MAIN,
)
from ...elements.panel import GUIPanel
from ...utils.align import table_wrapper
from .config import GUIConfigPanel
from .converter import GUIConverterPanel
from .reconstructor import GUIReconstructorPanel


class GUIMainPanel(GUIPanel):
    def __init__(
        self,
        config_panel: GUIConfigPanel,
        reconstructor_panel: GUIReconstructorPanel,
        converter_panel: GUIConverterPanel,
    ) -> None:
        self.config_panel = config_panel
        self.reconstructor_panel = reconstructor_panel
        self.converter_panel = converter_panel

        super().__init__(
            tag=TAG_PANEL_MAIN,
            parent=f"{TAG_TAB_MAIN}{SUF_CENTER_PANEL}",
        )

    def create_panel(self) -> None:
        with dpg.group(tag=self.tag):
            with dpg.child_window(
                tag=TAG_PANEL_MAIN_SETTINGS,
                parent=self.tag,
                width=-1,
                height=-DIM_PANEL_CONVERTER_HEIGHT - 4,
            ):
                self._create_settings()

            self._create_converter()

    @table_wrapper(columns=2, height=0)
    def _create_settings(self) -> None:
        with dpg.table_cell(tag=TAG_PANEL_MAIN_CONFIG_CELL):
            self.config_panel.create_panel()
        with dpg.table_cell(tag=TAG_PANEL_MAIN_RECONSTRUCTOR_CELL):
            self.reconstructor_panel.create_panel()

    def _create_converter(self) -> None:
        self.converter_panel.create_panel()
