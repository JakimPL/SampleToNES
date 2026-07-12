from typing import Any, Callable, List, Optional, Union

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.global_ import StatusElements
from sampletones_application.categories.elements.instructions import (
    InstructionsDetailsElements,
)
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.categories.pitch import build_pitch_tooltip
from sampletones_application.layout.general import GeneralLayout
from sampletones_application.layout.instructions import InstructionsLayout
from sampletones_application.tags.general import SUF_HANDLER_REGISTRY
from sampletones_application.tags.instructions import (
    TAG_INSTRUCTIONS_DETAILS_CHECKBOX_INSTRUCTIONS_CHOICE_NOISE_SHORT,
    TAG_INSTRUCTIONS_DETAILS_GROUP_INSTRUCTIONS_CHOICE,
    TAG_INSTRUCTIONS_DETAILS_INPUT_INSTRUCTIONS_CHOICE_NOISE_PERIOD,
    TAG_INSTRUCTIONS_DETAILS_INPUT_INSTRUCTIONS_CHOICE_NOISE_VOLUME,
    TAG_INSTRUCTIONS_DETAILS_INPUT_INSTRUCTIONS_CHOICE_PULSE_DUTY_CYCLE,
    TAG_INSTRUCTIONS_DETAILS_INPUT_INSTRUCTIONS_CHOICE_PULSE_PITCH,
    TAG_INSTRUCTIONS_DETAILS_INPUT_INSTRUCTIONS_CHOICE_PULSE_VOLUME,
    TAG_INSTRUCTIONS_DETAILS_INPUT_INSTRUCTIONS_CHOICE_TRIANGLE_PITCH,
    TAG_INSTRUCTIONS_DETAILS_PANEL,
    TAG_INSTRUCTIONS_DETAILS_TEXT_INFO,
)
from sampletones_application.ui.elements.field import labeled_field
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.layout.card import card
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.elements.pitch_stepper import GUIPitchStepper
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.utils.gui.dpg import (
    dpg_configure_item,
    dpg_delete_children,
)
from sampletones_application.utils.gui.shortcuts.manager import ShortcutManager
from sampletones_application.view_model.instruction.data import InstructionPanelData
from sampletones_core.constants.enums import GeneratorClassName
from sampletones_core.constants.general import (
    MAX_DUTY_CYCLE,
    MAX_VOLUME,
)
from sampletones_core.instructions import (
    InstructionUnion,
    NoiseInstruction,
    PulseInstruction,
    TriangleInstruction,
)
from sampletones_core.utils.pitch_kind import (
    PERIOD_VALUE_KIND,
    PITCH_VALUE_KIND,
    PitchValueKind,
)
from sampletones_shared.utils.arrays import clamp


class GUIInstructionChoicePanel(GUIPanel):
    def __init__(
        self,
        shortcut_manager: ShortcutManager,
        *,
        layout: InstructionsLayout,
        general_layout: GeneralLayout,
        language_manager: LanguageManager,
        status_bar: GUIStatusBar,
    ) -> None:
        self.on_instruction_parameter_changed: Optional[Callable[[InstructionUnion], None]] = None

        self._status_bar = status_bar
        self._shortcut_manager = shortcut_manager
        self._layout = layout
        self._general_layout = general_layout
        self._item_handler_tag = f"{TAG_INSTRUCTIONS_DETAILS_PANEL}{SUF_HANDLER_REGISTRY}"
        self._current_instruction_data: Optional[InstructionPanelData] = None
        self._pitch_stepper: Optional[GUIPitchStepper] = None

        self._lbl_section = language_manager[
            Page.INSTRUCTIONS,
            Panel.DETAILS,
            TextType.LABEL,
            InstructionsDetailsElements.DETAILS_TEXT,
        ]
        self._lbl_window_pulse_pitch = language_manager[
            Page.INSTRUCTIONS,
            Panel.DETAILS,
            TextType.LABEL,
            InstructionsDetailsElements.WINDOW_PULSE_PITCH,
        ]
        self._lbl_window_pulse_volume = language_manager[
            Page.INSTRUCTIONS,
            Panel.DETAILS,
            TextType.LABEL,
            InstructionsDetailsElements.WINDOW_PULSE_VOLUME,
        ]
        self._lbl_window_pulse_duty_cycle = language_manager[
            Page.INSTRUCTIONS,
            Panel.DETAILS,
            TextType.LABEL,
            InstructionsDetailsElements.WINDOW_PULSE_DUTY_CYCLE,
        ]
        self._lbl_window_noise_period = language_manager[
            Page.INSTRUCTIONS,
            Panel.DETAILS,
            TextType.LABEL,
            InstructionsDetailsElements.WINDOW_NOISE_PERIOD,
        ]
        self._lbl_window_noise_volume = language_manager[
            Page.INSTRUCTIONS,
            Panel.DETAILS,
            TextType.LABEL,
            InstructionsDetailsElements.WINDOW_NOISE_VOLUME,
        ]
        self._lbl_window_noise_short = language_manager[
            Page.INSTRUCTIONS,
            Panel.DETAILS,
            TextType.LABEL,
            InstructionsDetailsElements.WINDOW_NOISE_SHORT,
        ]
        self._lbl_window_triangle_pitch = language_manager[
            Page.INSTRUCTIONS,
            Panel.DETAILS,
            TextType.LABEL,
            InstructionsDetailsElements.WINDOW_TRIANGLE_PITCH,
        ]
        self._msg_no_instruction = language_manager[
            Page.INSTRUCTIONS,
            Panel.DETAILS,
            TextType.MESSAGE,
            InstructionsDetailsElements.NO_INSTRUCTION_SELECTED,
        ]
        self._msg_status_input = language_manager[
            Page.GLOBAL,
            Panel.STATUS,
            TextType.MESSAGE,
            StatusElements.INPUT,
        ]
        self._msg_status_input_pitch = language_manager[
            Page.INSTRUCTIONS,
            Panel.DETAILS,
            TextType.MESSAGE,
            InstructionsDetailsElements.STATUS_INPUT_PITCH,
        ]
        self._msg_status_input_period = language_manager[
            Page.INSTRUCTIONS,
            Panel.DETAILS,
            TextType.MESSAGE,
            InstructionsDetailsElements.STATUS_INPUT_PERIOD,
        ]
        tooltip_template = language_manager[
            Page.INSTRUCTIONS,
            Panel.DETAILS,
            TextType.TEMPLATE,
            InstructionsDetailsElements.PITCH_TOOLTIP_TEMPLATE,
        ]
        self._pitch_tooltip = build_pitch_tooltip(language_manager, PITCH_VALUE_KIND, tooltip_template)
        self._period_tooltip = build_pitch_tooltip(language_manager, PERIOD_VALUE_KIND, tooltip_template)

        super().__init__(
            tag=TAG_INSTRUCTIONS_DETAILS_PANEL,
        )

    def create_panel(self, parent: str) -> None:
        self._setup_handlers()
        with card(parent, self.tag, width=-1):
            self._create_section_text()
            self._create_instructions_choice_inputs()
            self._create_no_instruction_text()

    def update_choice(self, instruction_data: Optional[InstructionPanelData]) -> None:
        self._current_instruction_data = instruction_data
        dpg_configure_item(TAG_INSTRUCTIONS_DETAILS_TEXT_INFO, show=instruction_data is None)
        self._update_instructions_choice_panel(instruction_data)

    def _setup_handlers(self) -> None:
        with dpg.item_handler_registry(tag=self._item_handler_tag):
            dpg.add_item_deactivated_after_edit_handler(
                callback=self._on_instruction_changed,
                parent=self._item_handler_tag,
            )

    def _create_section_text(self) -> None:
        self._create_section_header(
            self._lbl_section,
            glyph=self._glyphs.headers.details,
        )

    def _create_no_instruction_text(self) -> None:
        dpg.add_text(
            self._msg_no_instruction,
            tag=TAG_INSTRUCTIONS_DETAILS_TEXT_INFO,
            parent=self.tag,
        )

    def _create_instructions_choice_inputs(self) -> None:
        with dpg.child_window(
            tag=TAG_INSTRUCTIONS_DETAILS_GROUP_INSTRUCTIONS_CHOICE,
            parent=self.tag,
            auto_resize_y=True,
            border=False,
        ):
            pass

    def _update_instructions_choice_panel(self, instruction_data: Optional[InstructionPanelData]) -> None:
        dpg_delete_children(TAG_INSTRUCTIONS_DETAILS_GROUP_INSTRUCTIONS_CHOICE)
        if instruction_data is None:
            return

        generator_type = instruction_data.generator_class_name
        instruction = instruction_data.instruction
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

    def _create_pitch_stepper(
        self,
        *,
        kind: PitchValueKind,
        initial_value: int,
        label: str,
        tag: str,
    ) -> None:
        is_period = kind is PERIOD_VALUE_KIND
        self._pitch_stepper = GUIPitchStepper(
            tag=tag,
            parent=TAG_INSTRUCTIONS_DETAILS_GROUP_INSTRUCTIONS_CHOICE,
            kind=kind,
            initial_value=initial_value,
            label=label,
            tooltip=self._period_tooltip if is_period else self._pitch_tooltip,
            status_message=self._msg_status_input_period if is_period else self._msg_status_input_pitch,
            status_bar=self._status_bar,
            layout=self._general_layout.pitch_stepper,
            value_color=self._general_layout.colors.text.disabled,
            shortcut_manager=self._shortcut_manager,
        )
        self._pitch_stepper.on_value_changed = self._on_pitch_value_changed

    def _on_pitch_value_changed(self, value: int) -> None:
        self._on_instruction_changed()

    def _create_pulse_instruction_choice_panel(self, instruction: PulseInstruction) -> None:
        self._create_pitch_stepper(
            kind=PITCH_VALUE_KIND,
            initial_value=instruction.pitch,
            label=self._lbl_window_pulse_pitch,
            tag=TAG_INSTRUCTIONS_DETAILS_INPUT_INSTRUCTIONS_CHOICE_PULSE_PITCH,
        )
        with labeled_field(
            self._lbl_window_pulse_volume,
            self._layout.instruction_choice.label_width,
            parent=TAG_INSTRUCTIONS_DETAILS_GROUP_INSTRUCTIONS_CHOICE,
        ):
            dpg.add_slider_int(
                tag=TAG_INSTRUCTIONS_DETAILS_INPUT_INSTRUCTIONS_CHOICE_PULSE_VOLUME,
                default_value=instruction.volume,
                min_value=1,
                max_value=MAX_VOLUME,
                clamped=True,
                width=self._layout.instruction_choice.input_width,
            )
        with labeled_field(
            self._lbl_window_pulse_duty_cycle,
            self._layout.instruction_choice.label_width,
            parent=TAG_INSTRUCTIONS_DETAILS_GROUP_INSTRUCTIONS_CHOICE,
        ):
            dpg.add_slider_int(
                tag=TAG_INSTRUCTIONS_DETAILS_INPUT_INSTRUCTIONS_CHOICE_PULSE_DUTY_CYCLE,
                default_value=instruction.duty_cycle,
                min_value=0,
                max_value=MAX_DUTY_CYCLE,
                clamped=True,
                width=self._layout.instruction_choice.input_width,
            )

        for tag in [
            TAG_INSTRUCTIONS_DETAILS_INPUT_INSTRUCTIONS_CHOICE_PULSE_VOLUME,
            TAG_INSTRUCTIONS_DETAILS_INPUT_INSTRUCTIONS_CHOICE_PULSE_DUTY_CYCLE,
        ]:
            self._status_bar.bind_to_item(tag, self._msg_status_input)
            dpg.bind_item_handler_registry(tag, self._item_handler_tag)
            FontRegistry.bind_to_item(tag, Font.MONO)

    def _create_triangle_instruction_choice_panel(self, instruction: TriangleInstruction) -> None:
        self._create_pitch_stepper(
            kind=PITCH_VALUE_KIND,
            initial_value=instruction.pitch,
            label=self._lbl_window_triangle_pitch,
            tag=TAG_INSTRUCTIONS_DETAILS_INPUT_INSTRUCTIONS_CHOICE_TRIANGLE_PITCH,
        )

    def _create_noise_instruction_choice_panel(self, instruction: NoiseInstruction) -> None:
        self._create_pitch_stepper(
            kind=PERIOD_VALUE_KIND,
            initial_value=instruction.period,
            label=self._lbl_window_noise_period,
            tag=TAG_INSTRUCTIONS_DETAILS_INPUT_INSTRUCTIONS_CHOICE_NOISE_PERIOD,
        )
        with labeled_field(
            self._lbl_window_noise_volume,
            self._layout.instruction_choice.label_width,
            parent=TAG_INSTRUCTIONS_DETAILS_GROUP_INSTRUCTIONS_CHOICE,
        ):
            dpg.add_slider_int(
                tag=TAG_INSTRUCTIONS_DETAILS_INPUT_INSTRUCTIONS_CHOICE_NOISE_VOLUME,
                default_value=instruction.volume,
                min_value=1,
                max_value=MAX_VOLUME,
                clamped=True,
                width=self._layout.instruction_choice.input_width,
            )
        dpg.add_checkbox(
            tag=TAG_INSTRUCTIONS_DETAILS_CHECKBOX_INSTRUCTIONS_CHOICE_NOISE_SHORT,
            parent=TAG_INSTRUCTIONS_DETAILS_GROUP_INSTRUCTIONS_CHOICE,
            label=self._lbl_window_noise_short,
            default_value=instruction.short,
            callback=self._on_instruction_changed,
        )

        self._status_bar.bind_to_item(
            TAG_INSTRUCTIONS_DETAILS_INPUT_INSTRUCTIONS_CHOICE_NOISE_VOLUME, self._msg_status_input
        )
        FontRegistry.bind_to_item(TAG_INSTRUCTIONS_DETAILS_INPUT_INSTRUCTIONS_CHOICE_NOISE_VOLUME, Font.MONO)
        self._status_bar.bind_to_item(
            TAG_INSTRUCTIONS_DETAILS_CHECKBOX_INSTRUCTIONS_CHOICE_NOISE_SHORT, self._msg_status_input
        )
        dpg.bind_item_handler_registry(
            TAG_INSTRUCTIONS_DETAILS_INPUT_INSTRUCTIONS_CHOICE_NOISE_VOLUME, self._item_handler_tag
        )

    def _on_instruction_changed(self, *_arguments: Any) -> None:
        if self._current_instruction_data is None:
            return

        assert self._pitch_stepper is not None, "Pitch stepper is built whenever an instruction is shown"

        instruction_data = self._current_instruction_data
        tags: List[str] = []
        values: List[Union[int, bool]] = []
        generator_type = instruction_data.generator_class_name
        instruction: InstructionUnion
        match generator_type:
            case GeneratorClassName.PULSE_GENERATOR:
                pitch = self._pitch_stepper.value
                volume = int(
                    clamp(dpg.get_value(TAG_INSTRUCTIONS_DETAILS_INPUT_INSTRUCTIONS_CHOICE_PULSE_VOLUME), 1, MAX_VOLUME)
                )
                duty_cycle = int(
                    clamp(
                        dpg.get_value(TAG_INSTRUCTIONS_DETAILS_INPUT_INSTRUCTIONS_CHOICE_PULSE_DUTY_CYCLE),
                        0,
                        MAX_DUTY_CYCLE,
                    )
                )
                instruction = PulseInstruction(
                    on=True,
                    pitch=pitch,
                    volume=volume,
                    duty_cycle=duty_cycle,
                )

                values = [volume, duty_cycle]
                tags = [
                    TAG_INSTRUCTIONS_DETAILS_INPUT_INSTRUCTIONS_CHOICE_PULSE_VOLUME,
                    TAG_INSTRUCTIONS_DETAILS_INPUT_INSTRUCTIONS_CHOICE_PULSE_DUTY_CYCLE,
                ]
            case GeneratorClassName.TRIANGLE_GENERATOR:
                instruction = TriangleInstruction(
                    on=True,
                    pitch=self._pitch_stepper.value,
                )
            case GeneratorClassName.NOISE_GENERATOR:
                volume = int(
                    clamp(dpg.get_value(TAG_INSTRUCTIONS_DETAILS_INPUT_INSTRUCTIONS_CHOICE_NOISE_VOLUME), 1, MAX_VOLUME)
                )
                short = bool(dpg.get_value(TAG_INSTRUCTIONS_DETAILS_CHECKBOX_INSTRUCTIONS_CHOICE_NOISE_SHORT))
                instruction = NoiseInstruction(
                    on=True,
                    period=self._pitch_stepper.value,
                    volume=volume,
                    short=short,
                )

                values = [volume]
                tags = [
                    TAG_INSTRUCTIONS_DETAILS_INPUT_INSTRUCTIONS_CHOICE_NOISE_VOLUME,
                ]

        for tag, value in zip(tags, values):
            dpg.set_value(tag, value)

        self.call(self.on_instruction_parameter_changed, instruction)
