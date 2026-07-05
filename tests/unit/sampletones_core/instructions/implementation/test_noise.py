import pytest

from sampletones_core.constants.enums import InstructionClassName
from sampletones_core.constants.general import MAX_VOLUME, NOISE_PERIODS
from sampletones_core.instructions.implementation.noise import NoiseInstruction
from sampletones_core.instructions.implementation.pulse import PulseInstruction


def _noise(
    period: int = 0,
    volume: int = 15,
    short: bool = False,
    on: bool = True,
) -> NoiseInstruction:
    return NoiseInstruction(on=on, period=period, volume=volume, short=short)


class TestNoiseInstructionName:
    def test_name_contains_period_frequency(self) -> None:
        instruction = _noise(period=0)
        assert str(NOISE_PERIODS[0]) in instruction.name

    def test_name_contains_volume_in_hex(self) -> None:
        assert "vF" in _noise(volume=15).name

    def test_name_long_mode_indicated_with_l(self) -> None:
        assert "l" in _noise(short=False).name

    def test_name_short_mode_indicated_with_s(self) -> None:
        assert "s" in _noise(short=True).name

    def test_name_prefixed_with_channel_letter(self) -> None:
        assert _noise().name.startswith("N ")


class TestNoiseInstructionOrdering:
    def test_lower_period_index_with_higher_frequency_sorts_correctly(self) -> None:
        low_freq = _noise(period=15)
        high_freq = _noise(period=0)
        assert low_freq < high_freq

    def test_higher_volume_sorts_before_lower_volume(self) -> None:
        assert _noise(period=5, volume=15) < _noise(period=5, volume=8)

    def test_wrong_type_raises_type_error(self) -> None:
        with pytest.raises(TypeError):
            _ = _noise() < PulseInstruction(
                on=True,
                pitch=60,
                volume=15,
                duty_cycle=0,
            )


class TestNoiseInstructionDistance:
    def test_both_silent_returns_zero(self) -> None:
        assert _noise(on=False).distance(_noise(on=False)) == 0.0

    def test_one_silent_returns_partial_penalty(self) -> None:
        audible = _noise(volume=MAX_VOLUME, on=True)
        silent = _noise(on=False)
        distance = audible.distance(silent)
        assert 0.0 < distance <= 0.5

    def test_equal_periods_nonzero_volume_returns_volume_diff(self) -> None:
        a = _noise(period=5, volume=15)
        b = _noise(period=5, volume=8)
        assert a.distance(b) > 0.0

    def test_different_periods_positive_distance(self) -> None:
        assert _noise(period=0).distance(_noise(period=15)) > 0.0

    def test_identical_instructions_distance_is_zero(self) -> None:
        instruction = _noise(period=3, volume=10)
        assert instruction.distance(instruction) == 0.0

    def test_distance_is_symmetric(self) -> None:
        a = _noise(period=2, volume=12)
        b = _noise(period=8, volume=6)
        assert abs(a.distance(b) - b.distance(a)) < 1e-9

    def test_wrong_type_raises_type_error(self) -> None:
        with pytest.raises(TypeError):
            _noise().distance(
                PulseInstruction(
                    on=True,
                    pitch=60,
                    volume=15,
                    duty_cycle=0,
                )
            )


class TestNoiseInstructionClassMethods:
    def test_null_instruction_is_off(self) -> None:
        assert NoiseInstruction.null_instruction().on is False

    def test_null_instruction_has_zero_volume(self) -> None:
        assert NoiseInstruction.null_instruction().volume == 0

    def test_default_instruction_is_on(self) -> None:
        assert NoiseInstruction.default_instruction().on is True

    def test_default_instruction_has_max_volume(self) -> None:
        assert NoiseInstruction.default_instruction().volume == MAX_VOLUME

    def test_class_name_returns_noise_instruction(self) -> None:
        assert NoiseInstruction.class_name() == InstructionClassName.NOISE_INSTRUCTION
