from typing import Dict

import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import GeneratorClassName, GeneratorName
from sampletones_core.generators.implementation.noise import NoiseGenerator
from sampletones_core.generators.implementation.pulse import PulseGenerator
from sampletones_core.generators.implementation.triangle import TriangleGenerator
from sampletones_core.generators.utils import (
    get_generator_by_instruction,
    get_generators_by_names,
    get_generators_map,
    get_remaining_generator_classes,
)
from sampletones_core.instructions import (
    NoiseInstruction,
    PulseInstruction,
    TriangleInstruction,
)


@pytest.fixture
def config() -> Config:
    return Config()


@pytest.fixture
def all_generators(config: Config) -> dict:
    return {
        GeneratorClassName.PULSE_GENERATOR: PulseGenerator(config, GeneratorName.PULSE1),
        GeneratorClassName.TRIANGLE_GENERATOR: TriangleGenerator(config, GeneratorName.TRIANGLE),
        GeneratorClassName.NOISE_GENERATOR: NoiseGenerator(config, GeneratorName.NOISE),
    }


class TestGetGeneratorsByNames:
    def test_pulse1_returns_pulse1(self, config: Config) -> None:
        result = get_generators_by_names(config, [GeneratorName.PULSE1])
        assert GeneratorName.PULSE1 in result
        assert isinstance(result[GeneratorName.PULSE1], PulseGenerator)

    def test_pulse2_without_pulse1_is_replaced_by_pulse1(self, config: Config) -> None:
        result = get_generators_by_names(config, [GeneratorName.PULSE2])
        assert GeneratorName.PULSE1 in result
        assert GeneratorName.PULSE2 not in result

    def test_multiple_names_all_returned(self, config: Config) -> None:
        result = get_generators_by_names(config, [GeneratorName.PULSE1, GeneratorName.TRIANGLE])
        assert GeneratorName.PULSE1 in result
        assert GeneratorName.TRIANGLE in result


class TestGetGeneratorsMap:
    def test_returns_all_generator_classes(self, config: Config) -> None:
        result = get_generators_map(config)
        assert GeneratorClassName.PULSE_GENERATOR in result
        assert GeneratorClassName.TRIANGLE_GENERATOR in result
        assert GeneratorClassName.NOISE_GENERATOR in result

    def test_generators_are_correct_types(self, config: Config) -> None:
        result = get_generators_map(config)
        assert isinstance(result[GeneratorClassName.PULSE_GENERATOR], PulseGenerator)
        assert isinstance(result[GeneratorClassName.TRIANGLE_GENERATOR], TriangleGenerator)
        assert isinstance(result[GeneratorClassName.NOISE_GENERATOR], NoiseGenerator)


class TestGetRemainingGeneratorClasses:
    def test_maps_by_class_name(self, config: Config) -> None:
        named = {
            GeneratorName.PULSE1: PulseGenerator(config, GeneratorName.PULSE1),
            GeneratorName.NOISE: NoiseGenerator(config, GeneratorName.NOISE),
        }
        result = get_remaining_generator_classes(named)
        assert GeneratorClassName.PULSE_GENERATOR in result
        assert GeneratorClassName.NOISE_GENERATOR in result


class TestGetGeneratorByInstruction:
    def test_pulse_instruction_returns_pulse_generator(self, all_generators: Dict) -> None:
        instruction = PulseInstruction(on=True, pitch=60, volume=15, duty_cycle=0)
        result = get_generator_by_instruction(instruction, all_generators)
        assert isinstance(result, PulseGenerator)

    def test_noise_instruction_returns_noise_generator(self, all_generators: Dict) -> None:
        instruction = NoiseInstruction(on=True, period=3, volume=15, short=False)
        result = get_generator_by_instruction(instruction, all_generators)
        assert isinstance(result, NoiseGenerator)

    def test_triangle_instruction_returns_triangle_generator(self, all_generators: Dict) -> None:
        instruction = TriangleInstruction(on=True, pitch=60)
        result = get_generator_by_instruction(instruction, all_generators)
        assert isinstance(result, TriangleGenerator)
