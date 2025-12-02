from typing import Any, Optional

import dearpygui.dearpygui as dpg

from sampletones.instructions import InstructionUnion
from sampletones.library import InstructionLibraryFragment

from ...constants import (
    LBL_INSTRUCTION_DETAILS,
    LBL_INSTRUCTION_GENERAL_HEADER,
    LBL_INSTRUCTION_PARAMETERS_HEADER,
    MSG_INSTRUCTION_NO_SELECTION,
    TAG_FONT_BOLD,
    TAG_INSTRUCTION_DETAILS,
    TAG_INSTRUCTION_DETAILS_GENERAL_HEADER,
    TAG_INSTRUCTION_DETAILS_GENERAL_TABLE,
    TAG_INSTRUCTION_DETAILS_INFO,
    TAG_INSTRUCTION_DETAILS_PARAMETERS_HEADER,
    TAG_INSTRUCTION_DETAILS_PARAMETERS_TABLE,
    TAG_INSTRUCTION_PANEL,
)
from ...elements.panel import GUIPanel
from ...elements.table.table import GUITable
from ...instruction.logic import InstructionDetailsLogic
from ...utils.dpg import dpg_configure_item


class GUIInstructionDetailsPanel(GUIPanel):
    def __init__(self) -> None:
        super().__init__(
            tag=TAG_INSTRUCTION_DETAILS,
            parent=TAG_INSTRUCTION_PANEL,
        )

        self.logic = InstructionDetailsLogic()
        self.general_table: Optional[GUITable] = None
        self.params_table: Optional[GUITable] = None

    def create_panel(self) -> None:
        with dpg.child_window(tag=self.tag, parent=self.parent):
            section_text = dpg.add_text(LBL_INSTRUCTION_DETAILS)
            dpg.bind_item_font(section_text, TAG_FONT_BOLD)

            dpg.add_separator()
            dpg.add_text(MSG_INSTRUCTION_NO_SELECTION, tag=TAG_INSTRUCTION_DETAILS_INFO)

            dpg.add_text(
                LBL_INSTRUCTION_GENERAL_HEADER,
                tag=TAG_INSTRUCTION_DETAILS_GENERAL_HEADER,
                show=False,
            )
            dpg.bind_item_font(TAG_INSTRUCTION_DETAILS_GENERAL_HEADER, TAG_FONT_BOLD)

            dpg.add_text(
                LBL_INSTRUCTION_PARAMETERS_HEADER,
                tag=TAG_INSTRUCTION_DETAILS_PARAMETERS_HEADER,
                show=False,
            )
            dpg.bind_item_font(TAG_INSTRUCTION_DETAILS_PARAMETERS_HEADER, TAG_FONT_BOLD)

    def display_instruction(
        self,
        generator_class_name: str,
        instruction: InstructionUnion,
        fragment: Optional[InstructionLibraryFragment[Any]] = None,
    ) -> None:
        self.logic.set_instruction_data(generator_class_name, instruction, fragment)
        self._update_display()

    def clear_display(self) -> None:
        self.logic.clear_data()
        self._update_display()

    def _update_display(self) -> None:
        table_data = self.logic.get_table_data()

        self._clear_tables()

        if table_data is None:
            dpg_configure_item(TAG_INSTRUCTION_DETAILS_INFO, show=True)
            dpg_configure_item(TAG_INSTRUCTION_DETAILS_GENERAL_HEADER, show=False)
            dpg_configure_item(TAG_INSTRUCTION_DETAILS_PARAMETERS_HEADER, show=False)
            return

        dpg_configure_item(TAG_INSTRUCTION_DETAILS_INFO, show=False)
        dpg_configure_item(TAG_INSTRUCTION_DETAILS_GENERAL_HEADER, show=True)
        dpg_configure_item(TAG_INSTRUCTION_DETAILS_PARAMETERS_HEADER, show=table_data.has_parameters)

        self.general_table = GUITable(
            tag=TAG_INSTRUCTION_DETAILS_GENERAL_TABLE,
            rows=table_data.general_rows,
            parent=self.tag,
            before=TAG_INSTRUCTION_DETAILS_PARAMETERS_HEADER,
        )

        if table_data.has_parameters:
            self.params_table = GUITable(
                tag=TAG_INSTRUCTION_DETAILS_PARAMETERS_TABLE,
                rows=table_data.parameter_rows,
                parent=self.tag,
            )

    def _clear_tables(self) -> None:
        if self.general_table is not None:
            self.general_table.delete_item()
            self.general_table = None

        if self.params_table is not None:
            self.params_table.delete_item()
            self.params_table = None
