from typing import Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.instructions import (
    InstructionsDetailsElements,
)
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.instructions import (
    TAG_INSTRUCTIONS_DETAILS_GROUP_TABLES,
    TAG_INSTRUCTIONS_DETAILS_HEADER_GENERAL,
    TAG_INSTRUCTIONS_DETAILS_HEADER_PARAMETERS,
    TAG_INSTRUCTIONS_DETAILS_PARAMETERS_CARD,
    TAG_INSTRUCTIONS_DETAILS_SECTION_PARAMETERS,
    TAG_INSTRUCTIONS_DETAILS_TABLE_GENERAL,
    TAG_INSTRUCTIONS_DETAILS_TABLE_PARAMETERS,
)
from sampletones_application.layout.general import TableColors, TablesLayout
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.layout.card import card
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
            tag=TAG_INSTRUCTIONS_DETAILS_PARAMETERS_CARD,
        )

    def create_panel(self, parent: str) -> None:
        with card(parent, self.tag, width=-1, show=False):
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
            parent=TAG_INSTRUCTIONS_DETAILS_PARAMETERS_CARD,
        ):
            self._create_section_header(
                self._lbl_parameters,
                glyph=self._glyphs.headers.parameters,
                parent=TAG_INSTRUCTIONS_DETAILS_GROUP_TABLES,
                tag=TAG_INSTRUCTIONS_DETAILS_SECTION_PARAMETERS,
            )

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
