import pytest

from sampletones_core.constants.enums import InstructionClassName
from sampletones_core.constants.general import MIN_PITCH
from sampletones_core.instructions.implementation.noise import NoiseInstruction
from sampletones_core.instructions.implementation.triangle import TriangleInstruction


def _tri(pitch: int = 60, on: bool = True) -> TriangleInstruction:
    return TriangleInstruction(on=on, pitch=pitch)


class TestTriangleInstructionName:
    def test_name_contains_note_name(self) -> None:
        assert "C-3" in _tri(pitch=60).name

    def test_name_prefixed_with_channel_letter(self) -> None:
        assert _tri().name.startswith("T ")


class TestTriangleInstructionOrdering:
    def test_lower_pitch_is_less(self) -> None:
        assert _tri(pitch=33) < _tri(pitch=60)

    def test_equal_pitches_not_less_than(self) -> None:
        assert not (_tri(pitch=60) < _tri(pitch=60))

    def test_wrong_type_raises_type_error(self) -> None:
        with pytest.raises(TypeError):
            _ = _tri() < NoiseInstruction(on=True, period=0, volume=15, short=False)


class TestTriangleInstructionClassMethods:
    def test_null_instruction_is_off(self) -> None:
        assert TriangleInstruction.null_instruction().on is False

    def test_null_instruction_has_min_pitch(self) -> None:
        assert TriangleInstruction.null_instruction().pitch == MIN_PITCH

    def test_default_instruction_is_on(self) -> None:
        assert TriangleInstruction.default_instruction().on is True

    def test_class_name_returns_triangle_instruction(self) -> None:
        assert TriangleInstruction.class_name() == InstructionClassName.TRIANGLE_INSTRUCTION
