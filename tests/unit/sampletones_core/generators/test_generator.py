import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.algorithm import MIN_SAMPLE_LENGTH
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.fft import CyclicArray
from sampletones_core.generators.implementation.pulse import PulseGenerator
from sampletones_core.instructions import PulseInstruction


@pytest.fixture
def config() -> Config:
    return Config()


@pytest.fixture
def generator(config: Config) -> PulseGenerator:
    return PulseGenerator(config, GeneratorName.PULSE1)


class TestGeneratorInit:
    def test_non_config_raises(self) -> None:
        with pytest.raises(TypeError):
            PulseGenerator("not_a_config", GeneratorName.PULSE1)

    def test_non_str_name_raises(self, config: Config) -> None:
        with pytest.raises(TypeError):
            PulseGenerator(config, 42)


class TestGeneratorFrameLength:
    def test_frame_length_matches_config(self, generator: PulseGenerator, config: Config) -> None:
        assert generator.frame_length == config.library.frame_length


class TestGeneratorReset:
    def test_reset_clears_previous_instruction(self, generator: PulseGenerator) -> None:
        instruction = PulseInstruction(on=True, pitch=60, volume=15, duty_cycle=0)
        generator.save_state(True, instruction)
        generator.reset()
        assert generator.previous_instruction is None

    def test_reset_resets_timer_phase(self, generator: PulseGenerator) -> None:
        generator.timer.phase = 0.5
        generator.reset()
        assert generator.timer.phase == 0.0


class TestGeneratorSaveState:
    def test_save_true_stores_instruction(self, generator: PulseGenerator) -> None:
        instruction = PulseInstruction(on=True, pitch=60, volume=15, duty_cycle=0)
        generator.save_state(True, instruction)
        assert generator.previous_instruction is instruction

    def test_save_false_does_not_store(self, generator: PulseGenerator) -> None:
        instruction = PulseInstruction(on=True, pitch=60, volume=15, duty_cycle=0)
        generator.save_state(False, instruction)
        assert generator.previous_instruction is None


class TestGeneratorInitials:
    def test_initials_reflect_timer_state(self, generator: PulseGenerator) -> None:
        generator.timer.phase = 0.3
        assert generator.initials == (0.3,)


class TestGeneratorGenerateSampleOff:
    def test_off_instruction_returns_zeros(self, generator: PulseGenerator) -> None:
        instruction = PulseInstruction(on=False, pitch=60, volume=0, duty_cycle=0)
        result = generator.generate_sample(instruction)
        assert isinstance(result, CyclicArray)
        assert np.all(result.array == 0.0)

    def test_off_instruction_returns_min_sample_length(self, generator: PulseGenerator, config: Config) -> None:
        instruction = PulseInstruction(on=False, pitch=60, volume=0, duty_cycle=0)
        result = generator.generate_sample(instruction)
        expected_length = round(MIN_SAMPLE_LENGTH * config.library.sample_rate)
        assert len(result.array) == expected_length

    def test_off_instruction_sample_rate_matches_config(self, generator: PulseGenerator, config: Config) -> None:
        instruction = PulseInstruction(on=False, pitch=60, volume=0, duty_cycle=0)
        result = generator.generate_sample(instruction)
        assert result.sample_rate == config.library.sample_rate
