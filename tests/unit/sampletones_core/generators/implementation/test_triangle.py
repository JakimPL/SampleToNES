import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, GeneratorClassName
from sampletones_core.constants.general import MIXER_TRIANGLE
from sampletones_core.generators.implementation.triangle import TriangleGenerator
from sampletones_core.instructions import PulseInstruction, TriangleInstruction


def _count_sign_changes(arr: np.ndarray) -> int:
    return int(np.sum(arr[:-1] * arr[1:] < 0))


@pytest.fixture
def config() -> Config:
    return Config()


@pytest.fixture
def generator(config: Config) -> TriangleGenerator:
    return TriangleGenerator(config, ChannelName.TRIANGLE)


class TestTriangleGeneratorCall:
    def test_wrong_instruction_type_raises(self, generator: TriangleGenerator) -> None:
        pulse = PulseInstruction(on=True, pitch=60, volume=15, duty_cycle=0)
        with pytest.raises(TypeError):
            generator(pulse)

    def test_off_instruction_returns_silence(self, generator: TriangleGenerator) -> None:
        instruction = TriangleInstruction(on=False, pitch=60)
        result = generator(instruction)
        assert np.all(result == 0.0)

    def test_off_instruction_returns_frame_length(self, generator: TriangleGenerator) -> None:
        instruction = TriangleInstruction(on=False, pitch=60)
        result = generator(instruction)
        assert len(result) == generator.frame_length

    def test_on_instruction_returns_frame_length(self, generator: TriangleGenerator) -> None:
        instruction = TriangleInstruction(on=True, pitch=60)
        result = generator(instruction)
        assert len(result) == generator.frame_length

    def test_on_instruction_result_is_float32(self, generator: TriangleGenerator) -> None:
        instruction = TriangleInstruction(on=True, pitch=60)
        result = generator(instruction)
        assert result.dtype == np.float32


class TestTriangleApply:
    def test_output_bounded_within_mixer_level(self, generator: TriangleGenerator) -> None:
        phase = np.linspace(0.0, 1.0, 100, endpoint=False, dtype=np.float32)
        instruction = TriangleInstruction(on=True, pitch=60)
        result = generator.apply(phase, instruction)
        assert np.all(result >= -MIXER_TRIANGLE - 1e-5)
        assert np.all(result <= MIXER_TRIANGLE + 1e-5)

    def test_at_phase_zero_output_is_maximum(self, generator: TriangleGenerator) -> None:
        phase = np.array([0.0], dtype=np.float32)
        instruction = TriangleInstruction(on=True, pitch=60)
        result = generator.apply(phase, instruction)
        assert float(result[0]) == pytest.approx(MIXER_TRIANGLE, abs=1e-5)

    def test_at_phase_half_output_is_minimum(self, generator: TriangleGenerator) -> None:
        phase = np.array([0.5], dtype=np.float32)
        instruction = TriangleInstruction(on=True, pitch=60)
        result = generator.apply(phase, instruction)
        assert float(result[0]) == pytest.approx(-MIXER_TRIANGLE, abs=1e-5)

    def test_result_dtype_is_float32(self, generator: TriangleGenerator) -> None:
        phase = np.array([0.0, 0.5], dtype=np.float32)
        instruction = TriangleInstruction(on=True, pitch=60)
        result = generator.apply(phase, instruction)
        assert result.dtype == np.float32


class TestTriangleGeneratorClassMethods:
    def test_class_name_returns_triangle_generator(self) -> None:
        assert TriangleGenerator.class_name() == GeneratorClassName.TRIANGLE_GENERATOR

    def test_get_instruction_type_returns_triangle_instruction(self) -> None:
        assert TriangleGenerator.get_instruction_type() == TriangleInstruction


class TestTriangleLevels:
    def test_output_has_sixteen_distinct_levels(self, generator: TriangleGenerator) -> None:
        # pitch=84: ~14.5 triangle cycles per frame (phase_increment=0.5 halves rate vs pulse)
        result = generator(TriangleInstruction(on=True, pitch=84))
        assert len(np.unique(result)) == 16

    def test_levels_are_approximately_uniformly_distributed(self, generator: TriangleGenerator) -> None:
        result = generator(TriangleInstruction(on=True, pitch=84))
        _, counts = np.unique(result, return_counts=True)
        cv = np.std(counts) / np.mean(counts)
        assert cv < 0.20


class TestTriangleMean:
    def test_mean_is_approximately_zero(self, generator: TriangleGenerator) -> None:
        # Symmetric wave: positive and negative halves cancel over complete cycles
        result = generator(TriangleInstruction(on=True, pitch=84))
        assert abs(np.mean(result)) < 0.05

    def test_output_spans_positive_and_negative(self, generator: TriangleGenerator) -> None:
        result = generator(TriangleInstruction(on=True, pitch=60))
        assert np.any(result > 0) and np.any(result < 0)


class TestTrianglePitch:
    def test_higher_pitch_produces_more_zero_crossings(self, generator: TriangleGenerator) -> None:
        # Triangle crosses zero twice per cycle; higher pitch → more cycles → more crossings
        low = generator(TriangleInstruction(on=True, pitch=40))
        high = generator(TriangleInstruction(on=True, pitch=100))
        assert _count_sign_changes(high) > _count_sign_changes(low)
