from typing import Any, Callable, List, Optional, Union

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.global_ import StatusElements
from sampletones_application.categories.elements.instructions import InstructionsDetailsElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.key import TextKey
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.general import (
    SUF_HANDLER_REGISTRY,
    SUF_PANEL_RIGHT,
    TAG_TAB_GLOBAL_INSTRUCTIONS,
)
from sampletones_application.constants.instructions import (
    TAG_CHECKBOX_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_NOISE_SHORT,
    TAG_GROUP_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE,
    TAG_GROUP_INSTRUCTIONS_DETAILS_TABLES,
    TAG_HEADER_INSTRUCTIONS_DETAILS_GENERAL,
    TAG_HEADER_INSTRUCTIONS_DETAILS_PARAMETERS,
    TAG_INPUT_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_NOISE_PERIOD,
    TAG_INPUT_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_NOISE_VOLUME,
    TAG_INPUT_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_PULSE_DUTY_CYCLE,
    TAG_INPUT_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_PULSE_PITCH,
    TAG_INPUT_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_PULSE_VOLUME,
    TAG_INPUT_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_TRIANGLE_PITCH,
    TAG_PANEL_INSTRUCTIONS_DETAILS,
    TAG_TABLE_INSTRUCTIONS_DETAILS_GENERAL,
    TAG_TABLE_INSTRUCTIONS_DETAILS_PARAMETERS,
    TAG_TEXT_INSTRUCTIONS_DETAILS_INFO,
)
from sampletones_application.layout.instructions import InstructionsLayout
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.elements.table.table import GUITable
from sampletones_application.utils.dpg import (
    dpg_configure_item,
    dpg_delete_children,
)
from sampletones_application.view_model.instruction.data import InstructionPanelData
from sampletones_application.view_model.instruction.details import InstructionDetailsPanelViewModel
from sampletones_application.view_model.instruction.table_data import InstructionTableData
from sampletones_core.constants.enums import GeneratorClassName
from sampletones_core.constants.general import (
    MAX_DUTY_CYCLE,
    MAX_PERIOD,
    MAX_PITCH,
    MAX_VOLUME,
    MIN_PITCH,
)
from sampletones_core.instructions import (
    InstructionUnion,
    NoiseInstruction,
    PulseInstruction,
    TriangleInstruction,
)
from sampletones_shared.types.application import Sender
from sampletones_shared.utils.arrays import clamp


class GUIInstructionDetailsPanel(GUIPanel):
    def __init__(
        self,
        *,
        layout: InstructionsLayout,
        language_manager: LanguageManager,
    ) -> None:
        self.on_instruction_parameter_changed: Optional[Callable[[InstructionUnion], None]] = None

        self.general_table: GUITable
        self.parameters_table: GUITable

        self._layout = layout
        self._item_handler_tag = f"{TAG_PANEL_INSTRUCTIONS_DETAILS}{SUF_HANDLER_REGISTRY}"
        self._current_viewmodel: Optional[InstructionDetailsPanelViewModel] = None

        self._lbl_section = language_manager[
            TextKey(
                Page.INSTRUCTIONS,
                Panel.DETAILS,
                TextType.LABEL,
                InstructionsDetailsElements.DETAILS_TEXT,
            )
        ]
        self._lbl_parameters = language_manager[
            TextKey(
                Page.INSTRUCTIONS,
                Panel.DETAILS,
                TextType.LABEL,
                InstructionsDetailsElements.PARAMETERS_TEXT,
            )
        ]
        self._lbl_general = language_manager[
            TextKey(
                Page.INSTRUCTIONS,
                Panel.DETAILS,
                TextType.LABEL,
                InstructionsDetailsElements.GENERAL_TEXT,
            )
        ]
        self._lbl_window_pulse_pitch = language_manager[
            TextKey(
                Page.INSTRUCTIONS,
                Panel.DETAILS,
                TextType.LABEL,
                InstructionsDetailsElements.WINDOW_PULSE_PITCH,
            )
        ]
        self._lbl_window_pulse_volume = language_manager[
            TextKey(
                Page.INSTRUCTIONS,
                Panel.DETAILS,
                TextType.LABEL,
                InstructionsDetailsElements.WINDOW_PULSE_VOLUME,
            )
        ]
        self._lbl_window_pulse_duty_cycle = language_manager[
            TextKey(
                Page.INSTRUCTIONS,
                Panel.DETAILS,
                TextType.LABEL,
                InstructionsDetailsElements.WINDOW_PULSE_DUTY_CYCLE,
            )
        ]
        self._lbl_window_noise_period = language_manager[
            TextKey(
                Page.INSTRUCTIONS,
                Panel.DETAILS,
                TextType.LABEL,
                InstructionsDetailsElements.WINDOW_NOISE_PERIOD,
            )
        ]
        self._lbl_window_noise_volume = language_manager[
            TextKey(
                Page.INSTRUCTIONS,
                Panel.DETAILS,
                TextType.LABEL,
                InstructionsDetailsElements.WINDOW_NOISE_VOLUME,
            )
        ]
        self._lbl_window_noise_short = language_manager[
            TextKey(
                Page.INSTRUCTIONS,
                Panel.DETAILS,
                TextType.LABEL,
                InstructionsDetailsElements.WINDOW_NOISE_SHORT,
            )
        ]
        self._lbl_window_triangle_pitch = language_manager[
            TextKey(
                Page.INSTRUCTIONS,
                Panel.DETAILS,
                TextType.LABEL,
                InstructionsDetailsElements.WINDOW_TRIANGLE_PITCH,
            )
        ]
        self._msg_no_instruction = language_manager[
            TextKey(
                Page.INSTRUCTIONS,
                Panel.DETAILS,
                TextType.MESSAGE,
                InstructionsDetailsElements.NO_INSTRUCTION_SELECTED,
            )
        ]
        self._msg_status_input = language_manager[
            TextKey(
                Page.GLOBAL,
                Panel.STATUS,
                TextType.MESSAGE,
                StatusElements.INPUT,
            )
        ]

        super().__init__(
            tag=TAG_PANEL_INSTRUCTIONS_DETAILS,
            parent=f"{TAG_TAB_GLOBAL_INSTRUCTIONS}{SUF_PANEL_RIGHT}",
        )

    def create_panel(self) -> None:
        self._setup_handlers()
        with dpg.child_window(
            tag=self.tag,
            parent=self.parent,
            width=self.width,
            height=self.height,
            border=False,
        ):
            self._create_section_text()
            self._create_instructions_choice_inputs()
            self._create_instruction_tables()

    def _setup_handlers(self) -> None:
        with dpg.item_handler_registry(tag=self._item_handler_tag):
            dpg.add_item_deactivated_after_edit_handler(
                callback=self._on_instruction_changed,
                parent=self._item_handler_tag,
            )
            dpg.add_item_edited_handler(
                callback=self._on_instruction_changed,
                parent=self._item_handler_tag,
            )

    def _create_section_text(self) -> None:
        section_text = dpg.add_text(self._lbl_section)
        FontRegistry.bind_to_item(section_text, Font.BOLD)

    def _create_instruction_tables(self) -> None:
        with dpg.group(
            tag=TAG_GROUP_INSTRUCTIONS_DETAILS_TABLES,
            parent=self.tag,
        ):
            dpg.add_separator()
            dpg.add_text(
                self._msg_no_instruction,
                tag=TAG_TEXT_INSTRUCTIONS_DETAILS_INFO,
                parent=TAG_GROUP_INSTRUCTIONS_DETAILS_TABLES,
            )

            dpg.add_text(
                self._lbl_general,
                tag=TAG_HEADER_INSTRUCTIONS_DETAILS_GENERAL,
                parent=TAG_GROUP_INSTRUCTIONS_DETAILS_TABLES,
                show=False,
            )

            self.general_table = GUITable(
                tag=TAG_TABLE_INSTRUCTIONS_DETAILS_GENERAL,
                parent=TAG_GROUP_INSTRUCTIONS_DETAILS_TABLES,
                rows=tuple(),
                before=TAG_HEADER_INSTRUCTIONS_DETAILS_PARAMETERS,
            )

            dpg.add_text(
                self._lbl_parameters,
                tag=TAG_HEADER_INSTRUCTIONS_DETAILS_PARAMETERS,
                parent=TAG_GROUP_INSTRUCTIONS_DETAILS_TABLES,
                show=False,
            )

            self.parameters_table = GUITable(
                tag=TAG_TABLE_INSTRUCTIONS_DETAILS_PARAMETERS,
                parent=TAG_GROUP_INSTRUCTIONS_DETAILS_TABLES,
                rows=tuple(),
            )

            FontRegistry.bind_to_item(
                TAG_HEADER_INSTRUCTIONS_DETAILS_GENERAL,
                Font.BOLD,
            )
            FontRegistry.bind_to_item(
                TAG_HEADER_INSTRUCTIONS_DETAILS_PARAMETERS,
                Font.BOLD,
            )

    def update_view(self, viewmodel: InstructionDetailsPanelViewModel) -> None:
        self._current_viewmodel = viewmodel
        self._update_tables(viewmodel.table_data)
        self._update_instructions_choice_panel(viewmodel.instruction_data)

    def _update_tables(self, table_data: Optional[InstructionTableData]) -> None:
        if table_data is None:
            dpg_configure_item(
                TAG_TEXT_INSTRUCTIONS_DETAILS_INFO,
                show=True,
            )
            dpg_configure_item(
                TAG_HEADER_INSTRUCTIONS_DETAILS_GENERAL,
                show=False,
            )
            dpg_configure_item(
                TAG_HEADER_INSTRUCTIONS_DETAILS_PARAMETERS,
                show=False,
            )
            return

        dpg_configure_item(TAG_TEXT_INSTRUCTIONS_DETAILS_INFO, show=False)
        dpg_configure_item(TAG_HEADER_INSTRUCTIONS_DETAILS_GENERAL, show=True)
        dpg_configure_item(
            TAG_HEADER_INSTRUCTIONS_DETAILS_PARAMETERS,
            show=table_data.has_parameters,
        )

        self.parameters_table.update_rows(table_data.parameter_rows)
        self.general_table.update_rows(table_data.general_rows)

    def _create_instructions_choice_inputs(self) -> None:
        with dpg.child_window(
            tag=TAG_GROUP_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE,
            parent=self.tag,
            height=self._layout.dimensions.instruction_choice_height,
            border=False,
        ):
            pass

    def _update_instructions_choice_panel(self, instruction_data: Optional[InstructionPanelData]) -> None:
        dpg_delete_children(TAG_GROUP_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE)
        if instruction_data is None:
            return

        generator_type = instruction_data.generator_class_name
        instruction = instruction_data.instruction
        dpg.add_separator(parent=TAG_GROUP_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE)
        match generator_type:
            case GeneratorClassName.PULSE_GENERATOR:
                assert isinstance(instruction, PulseInstruction)
                self._create_pulse_instruction_choice_panel(instruction)
            case GeneratorClassName.TRIANGLE_GENERATOR:
                assert isinstance(instruction, TriangleInstruction)
                self._create_triangle_instruction_choice_panel(instruction)
            case GeneratorClassName.NOISE_GENERATOR:
                assert isinstance(instruction, NoiseInstruction)
                self._create_noise_instruction_choice_panel(instruction)

    def _create_pulse_instruction_choice_panel(self, instruction: PulseInstruction) -> None:
        dpg.add_slider_int(
            tag=TAG_INPUT_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_PULSE_PITCH,
            parent=TAG_GROUP_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE,
            label=self._lbl_window_pulse_pitch,
            default_value=instruction.pitch,
            min_value=MIN_PITCH,
            max_value=MAX_PITCH,
            clamped=True,
            width=self._layout.dimensions.instruction_choice_input_width,
        )
        dpg.add_slider_int(
            tag=TAG_INPUT_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_PULSE_VOLUME,
            parent=TAG_GROUP_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE,
            label=self._lbl_window_pulse_volume,
            default_value=instruction.volume,
            min_value=1,
            max_value=MAX_VOLUME,
            clamped=True,
            width=self._layout.dimensions.instruction_choice_input_width,
        )
        dpg.add_slider_int(
            tag=TAG_INPUT_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_PULSE_DUTY_CYCLE,
            parent=TAG_GROUP_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE,
            label=self._lbl_window_pulse_duty_cycle,
            default_value=instruction.duty_cycle,
            min_value=0,
            max_value=MAX_DUTY_CYCLE,
            clamped=True,
            width=self._layout.dimensions.instruction_choice_input_width,
        )

        for tag in [
            TAG_INPUT_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_PULSE_PITCH,
            TAG_INPUT_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_PULSE_VOLUME,
            TAG_INPUT_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_PULSE_DUTY_CYCLE,
        ]:
            GUIStatusBar.bind_to_item(tag, self._msg_status_input)
            dpg.bind_item_handler_registry(tag, self._item_handler_tag)

    def _create_triangle_instruction_choice_panel(self, instruction: TriangleInstruction) -> None:
        dpg.add_slider_int(
            tag=TAG_INPUT_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_TRIANGLE_PITCH,
            parent=TAG_GROUP_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE,
            label=self._lbl_window_triangle_pitch,
            default_value=instruction.pitch,
            min_value=MIN_PITCH,
            max_value=MAX_PITCH,
            clamped=True,
            width=self._layout.dimensions.instruction_choice_input_width,
        )

        GUIStatusBar.bind_to_item(
            TAG_INPUT_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_TRIANGLE_PITCH,
            self._msg_status_input,
        )
        dpg.bind_item_handler_registry(
            TAG_INPUT_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_TRIANGLE_PITCH,
            self._item_handler_tag,
        )

    def _create_noise_instruction_choice_panel(self, instruction: NoiseInstruction) -> None:
        dpg.add_slider_int(
            tag=TAG_INPUT_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_NOISE_PERIOD,
            parent=TAG_GROUP_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE,
            label=self._lbl_window_noise_period,
            default_value=instruction.period,
            min_value=0,
            max_value=MAX_PERIOD,
            clamped=True,
            width=self._layout.dimensions.instruction_choice_input_width,
        )
        dpg.add_slider_int(
            tag=TAG_INPUT_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_NOISE_VOLUME,
            parent=TAG_GROUP_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE,
            label=self._lbl_window_noise_volume,
            default_value=instruction.volume,
            min_value=1,
            max_value=MAX_VOLUME,
            clamped=True,
            width=self._layout.dimensions.instruction_choice_input_width,
        )
        dpg.add_checkbox(
            tag=TAG_CHECKBOX_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_NOISE_SHORT,
            parent=TAG_GROUP_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE,
            label=self._lbl_window_noise_short,
            default_value=instruction.short,
            callback=self._on_instruction_changed,
        )

        for tag in [
            TAG_INPUT_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_NOISE_PERIOD,
            TAG_INPUT_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_NOISE_VOLUME,
            TAG_CHECKBOX_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_NOISE_SHORT,
        ]:
            GUIStatusBar.bind_to_item(tag, self._msg_status_input)
            if tag != TAG_CHECKBOX_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_NOISE_SHORT:
                dpg.bind_item_handler_registry(tag, self._item_handler_tag)

    def _on_instruction_changed(self, sender: Sender, app_data: int, user_data: Any) -> None:
        if self._current_viewmodel is None or self._current_viewmodel.instruction_data is None:
            return

        instruction_data = self._current_viewmodel.instruction_data
        tags: List[str] = []
        values: List[Union[int, bool]] = []
        generator_type = instruction_data.generator_class_name
        instruction: InstructionUnion
        match generator_type:
            case GeneratorClassName.PULSE_GENERATOR:
                pitch = dpg.get_value(TAG_INPUT_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_PULSE_PITCH)
                volume = dpg.get_value(TAG_INPUT_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_PULSE_VOLUME)
                duty_cycle = dpg.get_value(TAG_INPUT_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_PULSE_DUTY_CYCLE)

                pitch = int(clamp(pitch, MIN_PITCH, MAX_PITCH))
                volume = int(clamp(volume, 1, MAX_VOLUME))
                duty_cycle = int(clamp(duty_cycle, 0, MAX_DUTY_CYCLE))
                instruction = PulseInstruction(
                    on=True,
                    pitch=pitch,
                    volume=volume,
                    duty_cycle=duty_cycle,
                )

                values = [pitch, volume, duty_cycle]
                tags = [
                    TAG_INPUT_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_PULSE_PITCH,
                    TAG_INPUT_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_PULSE_VOLUME,
                    TAG_INPUT_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_PULSE_DUTY_CYCLE,
                ]
            case GeneratorClassName.TRIANGLE_GENERATOR:
                pitch = dpg.get_value(TAG_INPUT_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_TRIANGLE_PITCH)

                pitch = int(clamp(pitch, MIN_PITCH, MAX_PITCH))
                instruction = TriangleInstruction(
                    on=True,
                    pitch=pitch,
                )

                values = [pitch]
                tags = [
                    TAG_INPUT_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_TRIANGLE_PITCH,
                ]
            case GeneratorClassName.NOISE_GENERATOR:
                period = dpg.get_value(TAG_INPUT_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_NOISE_PERIOD)
                volume = dpg.get_value(TAG_INPUT_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_NOISE_VOLUME)
                short = dpg.get_value(TAG_CHECKBOX_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_NOISE_SHORT)

                period = int(clamp(period, 0, MAX_PERIOD))
                volume = int(clamp(volume, 1, MAX_VOLUME))
                short = bool(short)
                instruction = NoiseInstruction(
                    on=True,
                    period=period,
                    volume=volume,
                    short=short,
                )

                values = [period, volume, short]
                tags = [
                    TAG_INPUT_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_NOISE_PERIOD,
                    TAG_INPUT_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_NOISE_VOLUME,
                    TAG_CHECKBOX_INSTRUCTIONS_DETAILS_INSTRUCTIONS_CHOICE_NOISE_SHORT,
                ]

        for tag, value in zip(tags, values):
            dpg.set_value(tag, value)

        self.call(self.on_instruction_parameter_changed, instruction)
