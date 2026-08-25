import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, GeneratorClassName
from sampletones_core.constants.general import DUTY_CYCLES, MAX_VOLUME, MIXER_PULSE
from sampletones_core.generators.implementation.pulse import PulseGenerator
from sampletones_core.instructions import NoiseInstruction, PulseInstruction


def _count_sign_changes(arr: np.ndarray) -> int:
    return int(np.sum(arr[:-1] * arr[1:] < 0))


@pytest.fixture
def config() -> Config:
    return Config()


@pytest.fixture
def generator(config: Config) -> PulseGenerator:
    return PulseGenerator(config, ChannelName.PULSE1)


class TestPulseGeneratorCall:
    def test_wrong_instruction_type_raises(self, generator: PulseGenerator) -> None:
        noise = NoiseInstruction(on=True, period=3, volume=15, short=False)
        with pytest.raises(TypeError):
            generator(noise)

    def test_off_instruction_returns_silence(self, generator: PulseGenerator) -> None:
        instruction = PulseInstruction(on=False, pitch=60, volume=15, duty_cycle=0)
        result = generator(instruction)
        assert np.all(result == 0.0)

    def test_off_instruction_returns_frame_length(self, generator: PulseGenerator) -> None:
        instruction = PulseInstruction(on=False, pitch=60, volume=15, duty_cycle=0)
        result = generator(instruction)
        assert len(result) == generator.frame_length

    def test_on_instruction_returns_frame_length(self, generator: PulseGenerator) -> None:
        instruction = PulseInstruction(on=True, pitch=60, volume=15, duty_cycle=0)
        result = generator(instruction)
        assert len(result) == generator.frame_length

    def test_on_instruction_result_is_float32(self, generator: PulseGenerator) -> None:
        instruction = PulseInstruction(on=True, pitch=60, volume=15, duty_cycle=0)
        result = generator(instruction)
        assert result.dtype == np.float32


class TestPulseApply:
    def test_volume_zero_returns_all_zeros(self, generator: PulseGenerator) -> None:
        phase = np.array([0.1, 0.3, 0.6, 0.8], dtype=np.float32)
        instruction = PulseInstruction(on=True, pitch=60, volume=0, duty_cycle=2)
        result = generator.apply(phase, instruction)
        assert np.all(result == 0.0)

    def test_square_wave_duty_cycle_threshold(self, generator: PulseGenerator) -> None:
        # duty_cycle=2 maps to DUTY_CYCLES[2]=0.5; phase < 0.5 → +1, phase >= 0.5 → -1
        phase = np.array([0.1, 0.3, 0.5, 0.7], dtype=np.float32)
        instruction = PulseInstruction(on=True, pitch=60, volume=MAX_VOLUME, duty_cycle=2)
        result = generator.apply(phase, instruction)
        expected = np.array([MIXER_PULSE, MIXER_PULSE, -MIXER_PULSE, -MIXER_PULSE], dtype=np.float32)
        np.testing.assert_array_almost_equal(result, expected)

    def test_result_dtype_is_float32(self, generator: PulseGenerator) -> None:
        phase = np.array([0.1, 0.6], dtype=np.float32)
        instruction = PulseInstruction(on=True, pitch=60, volume=15, duty_cycle=0)
        result = generator.apply(phase, instruction)
        assert result.dtype == np.float32


class TestPulseGeneratorClassMethods:
    def test_class_name_returns_pulse_generator(self) -> None:
        assert PulseGenerator.class_name() == GeneratorClassName.PULSE_GENERATOR

    def test_get_instruction_type_returns_pulse_instruction(self) -> None:
        assert PulseGenerator.get_instruction_type() == PulseInstruction


class TestPulseBinaryWave:
    def test_output_is_predominantly_two_values(self, generator: PulseGenerator) -> None:
        result = generator(PulseInstruction(on=True, pitch=60, volume=15, duty_cycle=0))
        _, counts = np.unique(result, return_counts=True)
        top2_fraction = np.sum(np.sort(counts)[-2:]) / len(result)
        assert top2_fraction >= 0.90

    def test_dominant_values_have_opposite_signs(self, generator: PulseGenerator) -> None:
        result = generator(PulseInstruction(on=True, pitch=60, volume=15, duty_cycle=0))
        unique, counts = np.unique(result, return_counts=True)
        top2 = unique[np.argsort(counts)[-2:]]
        assert np.any(top2 < 0) and np.any(top2 > 0)

    def test_dominant_values_have_equal_magnitude(self, generator: PulseGenerator) -> None:
        result = generator(PulseInstruction(on=True, pitch=60, volume=15, duty_cycle=0))
        unique, counts = np.unique(result, return_counts=True)
        top2 = unique[np.argsort(counts)[-2:]]
        assert abs(abs(top2[0]) - abs(top2[1])) < 1e-3


class TestPulseDutyCycle:
    def test_wider_duty_cycle_increases_positive_fraction(self, generator: PulseGenerator) -> None:
        narrow = generator(PulseInstruction(on=True, pitch=60, volume=15, duty_cycle=0))
        wide = generator(PulseInstruction(on=True, pitch=60, volume=15, duty_cycle=2))
        assert np.sum(wide > 0) > np.sum(narrow > 0)

    def test_duty_cycle_fraction_matches_expected(self, generator: PulseGenerator) -> None:
        # pitch=84 gives ~29 cycles per frame, error ≤ 1/29 ≈ 3.4% per half-cycle
        result = generator(PulseInstruction(on=True, pitch=84, volume=15, duty_cycle=2))
        n_cycles = _count_sign_changes(result) // 2
        assert n_cycles >= 10, f"Too few cycles ({n_cycles}) for reliable duty cycle measurement"
        fraction = np.sum(result > 0) / len(result)
        assert abs(fraction - DUTY_CYCLES[2]) < 0.05


class TestPulseVolume:
    def test_higher_volume_increases_mean_amplitude(self, generator: PulseGenerator) -> None:
        low = generator(PulseInstruction(on=True, pitch=60, volume=7, duty_cycle=0))
        high = generator(PulseInstruction(on=True, pitch=60, volume=MAX_VOLUME, duty_cycle=0))
        assert np.mean(np.abs(high)) > np.mean(np.abs(low))

    def test_volume_scales_amplitude_linearly(self, generator: PulseGenerator) -> None:
        low = generator(PulseInstruction(on=True, pitch=60, volume=7, duty_cycle=0))
        high = generator(PulseInstruction(on=True, pitch=60, volume=MAX_VOLUME, duty_cycle=0))
        ratio = np.mean(np.abs(high)) / np.mean(np.abs(low))
        assert ratio == pytest.approx(MAX_VOLUME / 7, rel=0.02)


class TestPulsePitch:
    def test_higher_pitch_produces_more_sign_changes(self, generator: PulseGenerator) -> None:
        low = generator(PulseInstruction(on=True, pitch=40, volume=15, duty_cycle=0))
        high = generator(PulseInstruction(on=True, pitch=100, volume=15, duty_cycle=0))
        assert _count_sign_changes(high) > _count_sign_changes(low)
