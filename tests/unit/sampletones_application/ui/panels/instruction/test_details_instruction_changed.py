from types import SimpleNamespace
from typing import List

import pytest

from sampletones_application.ui.panels.instruction import details as details_module
from sampletones_application.ui.panels.instruction.details import GUIInstructionDetailsPanel
from sampletones_core.constants.enums import GeneratorClassName
from sampletones_core.instructions import InstructionUnion, NoiseInstruction, PulseInstruction, TriangleInstruction


@pytest.fixture(autouse=True)
def stub_dpg(monkeypatch: pytest.MonkeyPatch) -> None:
    """The volume, duty-cycle, and short controls are read straight from DearPyGui; the pitch and period
    come from the stepper. Returning fixed slider values isolates the rebuild from a live GUI."""
    monkeypatch.setattr(details_module.dpg, "get_value", lambda tag: 7)
    monkeypatch.setattr(details_module.dpg, "set_value", lambda tag, value: None)


def _panel(*, generator_class_name: GeneratorClassName, stepper_value: int) -> GUIInstructionDetailsPanel:
    panel = GUIInstructionDetailsPanel.__new__(GUIInstructionDetailsPanel)
    panel._current_viewmodel = SimpleNamespace(
        instruction_data=SimpleNamespace(generator_class_name=generator_class_name)
    )
    panel._pitch_stepper = SimpleNamespace(value=stepper_value)
    return panel


def _capture(panel: GUIInstructionDetailsPanel) -> List[InstructionUnion]:
    rebuilt: List[InstructionUnion] = []
    panel.on_instruction_parameter_changed = rebuilt.append
    return rebuilt


class TestInstructionRebuildReadsStepper:
    def test_pulse_pitch_comes_from_stepper(self) -> None:
        panel = _panel(generator_class_name=GeneratorClassName.PULSE_GENERATOR, stepper_value=72)
        rebuilt = _capture(panel)
        panel._on_instruction_changed()
        assert isinstance(rebuilt[0], PulseInstruction)
        assert rebuilt[0].pitch == 72

    def test_triangle_pitch_comes_from_stepper(self) -> None:
        panel = _panel(generator_class_name=GeneratorClassName.TRIANGLE_GENERATOR, stepper_value=64)
        rebuilt = _capture(panel)
        panel._on_instruction_changed()
        assert isinstance(rebuilt[0], TriangleInstruction)
        assert rebuilt[0].pitch == 64

    def test_noise_period_comes_from_stepper(self) -> None:
        panel = _panel(generator_class_name=GeneratorClassName.NOISE_GENERATOR, stepper_value=5)
        rebuilt = _capture(panel)
        panel._on_instruction_changed()
        assert isinstance(rebuilt[0], NoiseInstruction)
        assert rebuilt[0].period == 5

    def test_no_view_model_is_a_no_op(self) -> None:
        panel = GUIInstructionDetailsPanel.__new__(GUIInstructionDetailsPanel)
        panel._current_viewmodel = None
        rebuilt = _capture(panel)
        panel._on_instruction_changed()
        assert rebuilt == []
