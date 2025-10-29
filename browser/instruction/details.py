from typing import Optional

import dearpygui.dearpygui as dpg

from browser.instruction.logic import InstructionDetailsLogic
from browser.panel import GUIPanel
from constants.browser import (
    MSG_INSTRUCTION_DETAILS,
    MSG_INSTRUCTION_NO_SELECTION,
    TAG_INSTRUCTION_DETAILS,
    TAG_INSTRUCTION_DETAILS_INFO,
    TAG_INSTRUCTION_PANEL,
)
from library.data import LibraryFragment
from typehints.instructions import InstructionUnion


class GUIInstructionDetailsPanel(GUIPanel):
    def __init__(self) -> None:
        super().__init__(
            tag=TAG_INSTRUCTION_DETAILS,
            parent_tag=TAG_INSTRUCTION_PANEL,
        )

        self.logic = InstructionDetailsLogic()

    def create_panel(self) -> None:
        with dpg.group(tag=self.tag):
            dpg.add_text(MSG_INSTRUCTION_DETAILS)
            dpg.add_separator()
            dpg.add_text(MSG_INSTRUCTION_NO_SELECTION, tag=TAG_INSTRUCTION_DETAILS_INFO)

    def display_instruction(
        self, generator_class_name: str, instruction: InstructionUnion, fragment: Optional[LibraryFragment] = None
    ) -> None:
        self.logic.set_instruction_data(generator_class_name, instruction, fragment)
        self._update_display()

    def clear_display(self) -> None:
        self.logic.clear_data()
        self._update_display()

    def _update_display(self) -> None:
        display_text = self.logic.get_display_text()
        dpg.set_value(TAG_INSTRUCTION_DETAILS_INFO, display_text)
