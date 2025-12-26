from typing import Callable, Optional

import dearpygui.dearpygui as dpg

from sampletones.constants.enums import LibraryGeneratorName
from sampletones.constants.general import (
    MAX_DUTY_CYCLE,
    MAX_PERIOD,
    MAX_PITCH,
    MAX_VOLUME,
    MIN_PITCH,
)

from ...constants.general import SUF_PANEL_RIGHT, TAG_TAB_INSTRUCTIONS
from ...constants.instructions import (
    DIM_INPUT_WIDTH_INSTRUCTIONS_DETAILS_INSTRUCTION_CHOICE,
    DIM_PANEL_HEIGHT_INSTRUCTIONS_DETAILS_INSTRUCTION_CHOICE,
    LBL_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE,
    LBL_TEXT_INSTRUCTIONS_DETAILS_GENERAL,
    LBL_TEXT_INSTRUCTIONS_DETAILS_INSTRUCTION_DETAILS,
    LBL_TEXT_INSTRUCTIONS_DETAILS_PARAMETERS,
    LBL_WINDOW_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_NOISE_PERIOD,
    LBL_WINDOW_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_NOISE_SHORT,
    LBL_WINDOW_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_NOISE_VOLUME,
    LBL_WINDOW_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_PULSE_DUTY_CYCLE,
    LBL_WINDOW_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_PULSE_PITCH,
    LBL_WINDOW_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_PULSE_VOLUME,
    LBL_WINDOW_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_TRIANGLE_PITCH,
    MSG_INSTRUCTIONS_DETAILS_NO_SELECTION,
    TAG_INSTRUCTION_DETAILS_GENERAL_HEADER,
    TAG_INSTRUCTION_DETAILS_GENERAL_TABLE,
    TAG_INSTRUCTION_DETAILS_PARAMETERS_HEADER,
    TAG_INSTRUCTION_DETAILS_PARAMETERS_TABLE,
    TAG_PANEL_INSTRUCTIONS_DETAILS,
    TAG_TEXT_INSTRUCTIONS_DETAILS_INFO,
    TAG_WINDOW_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE,
    TAG_WINDOW_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_NOISE_PERIOD,
    TAG_WINDOW_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_NOISE_SHORT,
    TAG_WINDOW_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_NOISE_VOLUME,
    TAG_WINDOW_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_PULSE_PITCH,
    TAG_WINDOW_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_PULSE_VOLUME,
    TAG_WINDOW_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_TRIANGLE_PITCH,
)
from ...elements.fonts.font import Font
from ...elements.fonts.registry import FontRegistry
from ...elements.panel import GUIPanel
from ...elements.table.table import GUITable
from ...instruction.data import InstructionPanelData
from ...instruction.logic import InstructionDetailsLogic
from ...utils.dpg import dpg_configure_item, dpg_delete_children

OnInstructionLoaded = Callable[[], Optional[LibraryGeneratorName]]


class GUIInstructionDetailsPanel(GUIPanel):
    def __init__(self) -> None:
        self.logic = InstructionDetailsLogic()
        self.general_table: Optional[GUITable] = None
        self.params_table: Optional[GUITable] = None

        self._loaded_instruction_type: Optional[LibraryGeneratorName] = None

        self.is_instruction_loaded: Optional[OnInstructionLoaded] = None

        super().__init__(
            tag=TAG_PANEL_INSTRUCTIONS_DETAILS,
            parent=f"{TAG_TAB_INSTRUCTIONS}{SUF_PANEL_RIGHT}",
        )

    def create_panel(self) -> None:
        with dpg.child_window(
            tag=self.tag,
            parent=self.parent,
            width=self.width,
            height=self.height,
            border=False,
        ):
            self._create_section_text()
            self._create_instructions_choice_panel()
            self._create_instruction_tables()

    def _create_section_text(self) -> None:
        section_text = dpg.add_text(LBL_TEXT_INSTRUCTIONS_DETAILS_INSTRUCTION_DETAILS)
        FontRegistry.bind_to_item(section_text, Font.BOLD)

    def _create_instruction_tables(self) -> None:
        dpg.add_separator()
        dpg.add_text(MSG_INSTRUCTIONS_DETAILS_NO_SELECTION, tag=TAG_TEXT_INSTRUCTIONS_DETAILS_INFO)

        dpg.add_text(
            LBL_TEXT_INSTRUCTIONS_DETAILS_GENERAL,
            tag=TAG_INSTRUCTION_DETAILS_GENERAL_HEADER,
            show=False,
        )
        FontRegistry.bind_to_item(TAG_INSTRUCTION_DETAILS_GENERAL_HEADER, Font.BOLD)

        dpg.add_text(
            LBL_TEXT_INSTRUCTIONS_DETAILS_PARAMETERS,
            tag=TAG_INSTRUCTION_DETAILS_PARAMETERS_HEADER,
            show=False,
        )
        FontRegistry.bind_to_item(TAG_INSTRUCTION_DETAILS_PARAMETERS_HEADER, Font.BOLD)

    def display_instruction(
        self,
        instruction_data: InstructionPanelData,
    ) -> None:
        self.logic.current_data = instruction_data
        self._update_display()

    def clear_display(self) -> None:
        self.logic.clear_data()
        self._update_display()

    def _update_display(self) -> None:
        table_data = self.logic.get_table_data()

        self._clear_tables()

        if table_data is None:
            dpg_configure_item(TAG_TEXT_INSTRUCTIONS_DETAILS_INFO, show=True)
            dpg_configure_item(TAG_INSTRUCTION_DETAILS_GENERAL_HEADER, show=False)
            dpg_configure_item(TAG_INSTRUCTION_DETAILS_PARAMETERS_HEADER, show=False)
            return

        dpg_configure_item(TAG_TEXT_INSTRUCTIONS_DETAILS_INFO, show=False)
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

    def _create_instructions_choice_panel(self) -> None:
        with dpg.child_window(
            tag=TAG_WINDOW_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE,
            parent=self.tag,
            width=-1,
            height=DIM_PANEL_HEIGHT_INSTRUCTIONS_DETAILS_INSTRUCTION_CHOICE,
        ):
            self._create_instructions_choice_inputs()

    def _create_instructions_choice_inputs(self) -> None:
        section_text = dpg.add_text(
            LBL_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE,
            parent=TAG_WINDOW_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE,
        )
        FontRegistry.bind_to_item(section_text, Font.BOLD)
        instruction_type: Optional[LibraryGeneratorName] = self.call(self.is_instruction_loaded)
        if instruction_type is None:
            dpg.add_text("No instruction loaded.")
            return

        match instruction_type:
            case LibraryGeneratorName.PULSE:
                self._create_pulse_instruction_choice_panel()
            case LibraryGeneratorName.TRIANGLE:
                self._create_triangle_instruction_choice_panel()
            case LibraryGeneratorName.NOISE:
                self._create_noise_instruction_choice_panel()

    def _create_pulse_instruction_choice_panel(self) -> None:
        dpg.add_slider_int(
            tag=TAG_WINDOW_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_PULSE_PITCH,
            parent=TAG_WINDOW_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE,
            label=LBL_WINDOW_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_PULSE_PITCH,
            default_value=MIN_PITCH,
            min_value=MIN_PITCH,
            max_value=MAX_PITCH,
            width=DIM_INPUT_WIDTH_INSTRUCTIONS_DETAILS_INSTRUCTION_CHOICE,
        )
        dpg.add_slider_int(
            tag=TAG_WINDOW_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_PULSE_VOLUME,
            parent=TAG_WINDOW_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE,
            label=LBL_WINDOW_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_PULSE_VOLUME,
            default_value=MAX_VOLUME,
            min_value=0,
            max_value=MAX_VOLUME,
            width=DIM_INPUT_WIDTH_INSTRUCTIONS_DETAILS_INSTRUCTION_CHOICE,
        )
        dpg.add_slider_int(
            parent=TAG_WINDOW_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE,
            label=LBL_WINDOW_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_PULSE_DUTY_CYCLE,
            default_value=0,
            min_value=0,
            max_value=MAX_DUTY_CYCLE,
            width=DIM_INPUT_WIDTH_INSTRUCTIONS_DETAILS_INSTRUCTION_CHOICE,
        )

    def _create_triangle_instruction_choice_panel(self) -> None:
        dpg.add_slider_int(
            tag=TAG_WINDOW_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_TRIANGLE_PITCH,
            parent=TAG_WINDOW_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE,
            label=LBL_WINDOW_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_TRIANGLE_PITCH,
            default_value=MIN_PITCH,
            min_value=MIN_PITCH,
            max_value=MAX_PITCH,
            width=DIM_INPUT_WIDTH_INSTRUCTIONS_DETAILS_INSTRUCTION_CHOICE,
        )

    def _create_noise_instruction_choice_panel(self) -> None:
        dpg.add_slider_int(
            tag=TAG_WINDOW_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_NOISE_PERIOD,
            parent=TAG_WINDOW_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE,
            label=LBL_WINDOW_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_NOISE_PERIOD,
            default_value=0,
            min_value=0,
            max_value=MAX_PERIOD,
            width=DIM_INPUT_WIDTH_INSTRUCTIONS_DETAILS_INSTRUCTION_CHOICE,
        )
        dpg.add_slider_int(
            tag=TAG_WINDOW_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_NOISE_VOLUME,
            parent=TAG_WINDOW_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE,
            label=LBL_WINDOW_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_NOISE_VOLUME,
            default_value=MAX_VOLUME,
            min_value=0,
            max_value=MAX_VOLUME,
            width=DIM_INPUT_WIDTH_INSTRUCTIONS_DETAILS_INSTRUCTION_CHOICE,
        )
        dpg.add_checkbox(
            tag=TAG_WINDOW_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_NOISE_SHORT,
            parent=TAG_WINDOW_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE,
            label=LBL_WINDOW_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_NOISE_SHORT,
            default_value=False,
        )

    def _update_instructions_choice_panel(self) -> None:
        dpg_delete_children(TAG_WINDOW_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE)
        self._create_instructions_choice_inputs()
