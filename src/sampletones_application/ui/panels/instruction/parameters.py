from typing import Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.instructions import (
    InstructionsDetailsElements,
)
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.general import TableColors, TablesLayout
from sampletones_application.tags.instructions import (
    TAG_INSTRUCTIONS_DETAILS_GROUP_TABLES,
    TAG_INSTRUCTIONS_DETAILS_HEADER_GENERAL,
    TAG_INSTRUCTIONS_DETAILS_HEADER_PARAMETERS,
    TAG_INSTRUCTIONS_DETAILS_TABLE_GENERAL,
    TAG_INSTRUCTIONS_DETAILS_TABLE_PARAMETERS,
    TAG_INSTRUCTIONS_DETAILS_WINDOW_PARAMETERS_CARD,
)
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.elements.table.table import GUITable
from sampletones_application.utils.gui.dpg import dpg_configure_item
from sampletones_application.view_model.instruction.table_data import (
    InstructionTableData,
)


class GUIInstructionParametersPanel(GUIPanel):
    def __init__(
        self,
        *,
        table_colors: TableColors,
        table_layout: TablesLayout,
        language_manager: LanguageManager,
        initial_collapsed: bool = False,
    ) -> None:
        self.general_table: GUITable
        self.parameters_table: GUITable

        self._table_colors = table_colors
        self._table_layout = table_layout

        self._lbl_parameters = language_manager[
            Page.INSTRUCTIONS,
            Panel.DETAILS,
            TextType.LABEL,
            InstructionsDetailsElements.PARAMETERS_TEXT,
        ]
        self._lbl_general = language_manager[
            Page.INSTRUCTIONS,
            Panel.DETAILS,
            TextType.LABEL,
            InstructionsDetailsElements.GENERAL_TEXT,
        ]

        super().__init__(
            tag=TAG_INSTRUCTIONS_DETAILS_WINDOW_PARAMETERS_CARD,
        )
        self._enable_vertical_collapse(initial_collapsed=initial_collapsed, auto_height=True)

    def create_panel(self, parent: str) -> None:
        with self._collapsible_card(
            parent,
            self._lbl_parameters,
            glyph=self._glyphs.headers.parameters,
            show=False,
        ):
            self._create_instruction_tables()

    def update_tables(self, table_data: Optional[InstructionTableData]) -> None:
        if table_data is None:
            self.hide()
            return

        self.show()
        dpg_configure_item(
            TAG_INSTRUCTIONS_DETAILS_HEADER_PARAMETERS,
            show=table_data.has_parameters,
        )

        self.parameters_table.update_rows(table_data.parameter_rows)
        self.general_table.update_rows(table_data.general_rows)

    def _create_instruction_tables(self) -> None:
        with dpg.group(
            tag=TAG_INSTRUCTIONS_DETAILS_GROUP_TABLES,
            parent=self._body_container,
        ):
            dpg.add_text(
                self._lbl_general,
                tag=TAG_INSTRUCTIONS_DETAILS_HEADER_GENERAL,
                parent=TAG_INSTRUCTIONS_DETAILS_GROUP_TABLES,
            )

            self.general_table = GUITable(
                tag=TAG_INSTRUCTIONS_DETAILS_TABLE_GENERAL,
                parent=TAG_INSTRUCTIONS_DETAILS_GROUP_TABLES,
                rows=tuple(),
                label_column_width=self._table_layout.label_width,
                label_color=self._table_colors.label,
                value_color=self._table_colors.value,
            )

            dpg.add_text(
                self._lbl_parameters,
                tag=TAG_INSTRUCTIONS_DETAILS_HEADER_PARAMETERS,
                parent=TAG_INSTRUCTIONS_DETAILS_GROUP_TABLES,
                show=False,
            )

            self.parameters_table = GUITable(
                tag=TAG_INSTRUCTIONS_DETAILS_TABLE_PARAMETERS,
                parent=TAG_INSTRUCTIONS_DETAILS_GROUP_TABLES,
                rows=tuple(),
                label_column_width=self._table_layout.label_width,
                label_color=self._table_colors.label,
                value_color=self._table_colors.value,
            )

            FontRegistry.bind_to_item(
                TAG_INSTRUCTIONS_DETAILS_HEADER_GENERAL,
                Font.BOLD,
            )
            FontRegistry.bind_to_item(
                TAG_INSTRUCTIONS_DETAILS_HEADER_PARAMETERS,
                Font.BOLD,
            )
