import pytest

from sampletones_core.constants.enums import InstructionClassName
from sampletones_core.constants.general import MAX_VOLUME, MIN_PITCH
from sampletones_core.instructions.implementation.pulse import PulseInstruction
from sampletones_core.instructions.implementation.triangle import TriangleInstruction


def _pulse(
    pitch: int = 60,
    volume: int = 15,
    duty_cycle: int = 0,
    on: bool = True,
) -> PulseInstruction:
    return PulseInstruction(
        on=on,
        pitch=pitch,
        volume=volume,
        duty_cycle=duty_cycle,
    )


class TestPulseInstructionName:
    def test_name_contains_note_name(self) -> None:
        assert "C-3" in _pulse(pitch=60).name

    def test_name_contains_volume_in_hex(self) -> None:
        assert "vF" in _pulse(volume=15).name

    def test_name_contains_duty_percentage(self) -> None:
        assert "D25" in _pulse(duty_cycle=1).name

    def test_name_prefixed_with_channel_letter(self) -> None:
        assert _pulse().name.startswith("P ")


class TestPulseInstructionOrdering:
    def test_lower_pitch_is_less_than_higher_pitch(self) -> None:
        assert _pulse(pitch=33) < _pulse(pitch=60)

    def test_higher_volume_sorts_before_lower_volume(self) -> None:
        assert _pulse(pitch=60, volume=15) < _pulse(pitch=60, volume=8)

    def test_lower_duty_cycle_sorts_before_higher_at_same_pitch_volume(self) -> None:
        assert _pulse(pitch=60, volume=10, duty_cycle=0) < _pulse(
            pitch=60,
            volume=10,
            duty_cycle=1,
        )

    def test_comparison_with_wrong_type_raises_type_error(self) -> None:
        with pytest.raises(TypeError):
            _ = _pulse() < TriangleInstruction(on=True, pitch=60)


class TestPulseInstructionClassMethods:
    def test_null_instruction_is_off(self) -> None:
        assert PulseInstruction.null_instruction().on is False

    def test_null_instruction_has_zero_volume(self) -> None:
        assert PulseInstruction.null_instruction().volume == 0

    def test_null_instruction_has_min_pitch(self) -> None:
        assert PulseInstruction.null_instruction().pitch == MIN_PITCH

    def test_default_instruction_is_on(self) -> None:
        assert PulseInstruction.default_instruction().on is True

    def test_default_instruction_has_max_volume(self) -> None:
        assert PulseInstruction.default_instruction().volume == MAX_VOLUME

    def test_class_name_returns_pulse_instruction(self) -> None:
        assert PulseInstruction.class_name() == InstructionClassName.PULSE_INSTRUCTION
