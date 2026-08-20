import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, GeneratorClassName
from sampletones_core.constants.general import (
    MAX_VOLUME,
    MIXER_NOISE,
    MIXER_PULSE,
    NOISE_PERIODS,
)
from sampletones_core.generators.implementation.noise import NoiseGenerator
from sampletones_core.generators.implementation.pulse import PulseGenerator
from sampletones_core.instructions import NoiseInstruction, PulseInstruction
from tests.suite.noise import tone_frequency

FASTEST_PERIOD = len(NOISE_PERIODS) - 1
PERIODIC_PERIOD = 0
PERIODICITY_CORRELATION = 0.98


def _count_sign_changes(arr: np.ndarray) -> int:
    return int(np.sum(arr[:-1] * arr[1:] < 0))


@pytest.fixture
def config() -> Config:
    return Config()


@pytest.fixture
def generator(config: Config) -> NoiseGenerator:
    return NoiseGenerator(config, ChannelName.NOISE)


@pytest.fixture
def pulse_generator(config: Config) -> PulseGenerator:
    return PulseGenerator(config, ChannelName.PULSE1)


class TestNoiseGeneratorCall:
    def test_wrong_instruction_type_raises(self, generator: NoiseGenerator) -> None:
        pulse = PulseInstruction(on=True, pitch=60, volume=15, duty_cycle=0)
        with pytest.raises(TypeError):
            generator(pulse)

    def test_off_instruction_returns_silence(self, generator: NoiseGenerator) -> None:
        instruction = NoiseInstruction(on=False, period=0, volume=15, short=False)
        result = generator(instruction)
        assert np.all(result == 0.0)

    def test_off_instruction_returns_frame_length(self, generator: NoiseGenerator) -> None:
        instruction = NoiseInstruction(on=False, period=0, volume=15, short=False)
        result = generator(instruction)
        assert len(result) == generator.frame_length

    def test_on_instruction_returns_frame_length(self, generator: NoiseGenerator) -> None:
        instruction = NoiseInstruction(on=True, period=3, volume=15, short=False)
        result = generator(instruction)
        assert len(result) == generator.frame_length

    def test_on_instruction_result_is_float32(self, generator: NoiseGenerator) -> None:
        instruction = NoiseInstruction(on=True, period=3, volume=15, short=False)
        result = generator(instruction)
        assert result.dtype == np.float32


class TestNoiseApply:
    def test_volume_zero_returns_all_zeros(self, generator: NoiseGenerator) -> None:
        signal = np.array([1.0, -1.0], dtype=np.float32)
        instruction = NoiseInstruction(on=True, period=3, volume=0, short=False)
        result = generator.apply(signal, instruction)
        assert np.all(result == 0.0)

    def test_max_volume_scales_by_mixer_level(self, generator: NoiseGenerator) -> None:
        signal = np.array([1.0, -1.0], dtype=np.float32)
        instruction = NoiseInstruction(on=True, period=3, volume=MAX_VOLUME, short=False)
        result = generator.apply(signal, instruction)
        expected_scale = np.float32(MIXER_NOISE)
        np.testing.assert_array_almost_equal(result, [expected_scale, -expected_scale])


class TestNoiseMixerBalance:
    def test_noise_to_pulse_level_ratio_matches_the_nes_mixer(
        self,
        generator: NoiseGenerator,
        pulse_generator: PulseGenerator,
    ) -> None:
        signal = np.array([1.0, -1.0], dtype=np.float32)
        noise = generator.apply(signal, NoiseInstruction(on=True, period=3, volume=MAX_VOLUME, short=False))
        pulse = pulse_generator.apply(signal, PulseInstruction(on=True, pitch=60, volume=MAX_VOLUME, duty_cycle=2))
        ratio = float(np.max(np.abs(noise))) / float(np.max(np.abs(pulse)))
        assert ratio == pytest.approx(MIXER_NOISE / MIXER_PULSE)


class TestNoiseLibrarySample:
    @pytest.mark.parametrize("short", [False, True], ids=["long", "short"])
    def test_sample_spans_whole_shift_register_cycles(
        self,
        generator: NoiseGenerator,
        config: Config,
        short: bool,
    ) -> None:
        instruction = NoiseInstruction(on=True, period=FASTEST_PERIOD, volume=MAX_VOLUME, short=short)
        sample = generator.generate_sample(instruction)
        cycle_samples = config.library.sample_rate / tone_frequency(FASTEST_PERIOD, short)
        cycles = len(sample.array) / cycle_samples
        assert cycles == pytest.approx(round(cycles), abs=0.05)

    def test_sample_halves_match_for_a_two_cycle_sample(self, generator: NoiseGenerator, config: Config) -> None:
        """A cycle spans a fractional number of output samples, so the halves compared here sit
        a fraction of a shift-register step apart. The slowest period holds that fraction far
        below one step, where the repetition shows as near-perfect correlation.
        """
        instruction = NoiseInstruction(on=True, period=PERIODIC_PERIOD, volume=MAX_VOLUME, short=True)
        cycle_samples = config.library.sample_rate / tone_frequency(PERIODIC_PERIOD, True)
        length = round(cycle_samples)
        generator.reset()
        rendered = np.concatenate(
            [generator(instruction, save=True) for _ in range(int(np.ceil(2 * length / generator.frame_length)))]
        )
        first = rendered[:length]
        second = rendered[length : 2 * length]
        assert float(np.corrcoef(first, second)[0, 1]) > PERIODICITY_CORRELATION


class TestNoiseGeneratorSetTimer:
    def test_on_instruction_sets_short_mode(self, generator: NoiseGenerator) -> None:
        instruction = NoiseInstruction(on=True, period=3, volume=15, short=True)
        generator.set_timer(instruction)
        assert generator.timer.short is True

    def test_on_instruction_clears_short_mode(self, generator: NoiseGenerator) -> None:
        generator.timer.short = True
        instruction = NoiseInstruction(on=True, period=3, volume=15, short=False)
        generator.set_timer(instruction)
        assert generator.timer.short is False

    def test_off_instruction_resets_short_to_false(self, generator: NoiseGenerator) -> None:
        generator.timer.short = True
        instruction = NoiseInstruction(on=False, period=0, volume=0, short=True)
        generator.set_timer(instruction)
        assert generator.timer.short is False


class TestNoiseGeneratorClassMethods:
    def test_class_name_returns_noise_generator(self) -> None:
        assert NoiseGenerator.class_name() == GeneratorClassName.NOISE_GENERATOR

    def test_get_instruction_type_returns_noise_instruction(self) -> None:
        assert NoiseGenerator.get_instruction_type() == NoiseInstruction


class TestNoiseBinaryWave:
    def test_output_is_strictly_binary(self, generator: NoiseGenerator) -> None:
        result = generator(NoiseInstruction(on=True, period=3, volume=15, short=False))
        assert len(np.unique(result)) == 2

    def test_binary_values_have_opposite_signs(self, generator: NoiseGenerator) -> None:
        result = generator(NoiseInstruction(on=True, period=3, volume=15, short=False))
        unique = np.unique(result)
        assert unique[0] < 0 and unique[1] > 0

    def test_binary_values_have_equal_magnitude(self, generator: NoiseGenerator) -> None:
        result = generator(NoiseInstruction(on=True, period=3, volume=15, short=False))
        unique = np.unique(result)
        assert abs(abs(unique[0]) - abs(unique[1])) < 1e-6


class TestNoiseShortMode:
    def test_short_mode_differs_from_long_mode(self, generator: NoiseGenerator) -> None:
        # Both start from the same LFSR state (save=False); only feedback bit differs
        long_result = generator(NoiseInstruction(on=True, period=8, volume=15, short=False))
        generator.reset()
        short_result = generator(NoiseInstruction(on=True, period=8, volume=15, short=True))
        assert not np.array_equal(long_result, short_result)


class TestNoisePeriod:
    def test_all_periods_produce_distinct_outputs(self, generator: NoiseGenerator) -> None:
        # NOISE_PERIODS[0]=4068 clocks (slowest) … NOISE_PERIODS[15]=4 clocks (fastest)
        outputs = set()
        for period in range(16):
            generator.reset()
            result = generator(NoiseInstruction(on=True, period=period, volume=15, short=False))
            outputs.add(result.tobytes())

        assert len(outputs) == 16

    def test_fastest_period_has_more_transitions_than_slowest(self, generator: NoiseGenerator) -> None:
        generator.reset()
        slow = generator(NoiseInstruction(on=True, period=0, volume=15, short=False))
        generator.reset()
        fast = generator(NoiseInstruction(on=True, period=15, volume=15, short=False))
        assert _count_sign_changes(fast) > _count_sign_changes(slow)


class TestNoiseMean:
    def test_mean_close_to_zero_at_high_frequency(self, generator: NoiseGenerator) -> None:
        # period=15 → 4 APU clocks/step → ~7400 LFSR steps per frame → reliable mean
        result = generator(NoiseInstruction(on=True, period=15, volume=15, short=False))
        assert abs(np.mean(result)) < 1e-2


class TestNoiseVolume:
    def test_higher_volume_increases_mean_amplitude(self, generator: NoiseGenerator) -> None:
        low = generator(NoiseInstruction(on=True, period=8, volume=7, short=False))
        high = generator(NoiseInstruction(on=True, period=8, volume=MAX_VOLUME, short=False))
        assert np.mean(np.abs(high)) > np.mean(np.abs(low))

    def test_volume_scales_amplitude_linearly(self, generator: NoiseGenerator) -> None:
        # Same LFSR sequence (save=False, same period), only scale differs
        low = generator(NoiseInstruction(on=True, period=8, volume=7, short=False))
        high = generator(NoiseInstruction(on=True, period=8, volume=MAX_VOLUME, short=False))
        ratio = np.mean(np.abs(high)) / np.mean(np.abs(low))
        assert ratio == pytest.approx(MAX_VOLUME / 7, rel=0.02)
