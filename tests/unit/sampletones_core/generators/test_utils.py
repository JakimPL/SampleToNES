import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, GeneratorClassName
from sampletones_core.generators.implementation.noise import NoiseGenerator
from sampletones_core.generators.implementation.pulse import PulseGenerator
from sampletones_core.generators.implementation.triangle import TriangleGenerator
from sampletones_core.generators.utils import (
    get_generators_by_channels,
    get_generators_map,
)


@pytest.fixture
def config() -> Config:
    return Config()


class TestGetGeneratorsByChannels:
    def test_pulse1_returns_pulse1(self, config: Config) -> None:
        result = get_generators_by_channels(config, [ChannelName.PULSE1])
        assert ChannelName.PULSE1 in result
        assert isinstance(result[ChannelName.PULSE1], PulseGenerator)

    def test_pulse2_without_pulse1_is_replaced_by_pulse1(self, config: Config) -> None:
        result = get_generators_by_channels(config, [ChannelName.PULSE2])
        assert ChannelName.PULSE1 in result
        assert ChannelName.PULSE2 not in result

    def test_multiple_names_all_returned(self, config: Config) -> None:
        result = get_generators_by_channels(config, [ChannelName.PULSE1, ChannelName.TRIANGLE])
        assert ChannelName.PULSE1 in result
        assert ChannelName.TRIANGLE in result


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
