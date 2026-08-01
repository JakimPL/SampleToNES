import numpy as np

from sampletones_core.constants.enums import FeatureKey
from sampletones_core.constants.general import NUM_PERIODS
from sampletones_core.exporters.implementation.noise import NoiseExporter
from sampletones_core.generators import NoiseGenerator
from sampletones_core.instructions.implementation.noise import NoiseInstruction


def _noise(
    period: int = 0,
    volume: int = 15,
    short: bool = False,
) -> NoiseInstruction:
    return NoiseInstruction(
        on=volume > 0,
        period=period,
        volume=volume,
        short=short,
    )


def _off() -> NoiseInstruction:
    return NoiseInstruction(
        on=False,
        period=0,
        volume=0,
        short=False,
    )


class TestNoiseExporterExtractData:
    def test_all_off_instructions_initial_period_is_zero(self) -> None:
        initial_period, _, _, _ = NoiseExporter.extract_data([_off(), _off()])
        assert initial_period == 0

    def test_initial_period_set_on_first_on_instruction(self) -> None:
        instructions = [_noise(period=7, volume=10)]
        initial_period, _, _, _ = NoiseExporter.extract_data(instructions)
        assert initial_period == 7

    def test_off_instructions_before_on_instruction_get_backfilled(self) -> None:
        instructions = [_off(), _noise(period=5, volume=8)]
        _, periods, _, _ = NoiseExporter.extract_data(instructions)
        assert periods[0] == 5

    def test_off_instruction_resets_volume_to_zero(self) -> None:
        instructions = [_noise(period=3, volume=12), _off()]
        _, _, volumes, _ = NoiseExporter.extract_data(instructions)
        assert volumes[1] == 0

    def test_trailing_nonzero_volume_appends_extra_zero(self) -> None:
        instructions = [_noise(period=0, volume=10)]
        _, _, volumes, _ = NoiseExporter.extract_data(instructions)
        assert volumes[-1] == 0
        assert len(volumes) == 2

    def test_duty_cycle_tracks_short_field(self) -> None:
        instructions = [_noise(period=0, volume=10, short=True)]
        _, _, _, duty_cycles = NoiseExporter.extract_data(instructions)
        assert duty_cycles[0] is True

    def test_empty_instruction_list(self) -> None:
        initial, periods, volumes, duty_cycles = NoiseExporter.extract_data([])
        assert initial == 0
        assert periods == []
        assert volumes == []
        assert duty_cycles == []


class TestNoiseExporterDeriveInitialPitch:
    def test_reference_is_the_first_sounding_period(self) -> None:
        instructions = [_off(), _noise(period=7, volume=10), _noise(period=2, volume=10)]
        assert NoiseExporter.derive_initial_pitch(instructions) == 7

    def test_empty_instruction_list_references_period_zero(self) -> None:
        assert NoiseExporter.derive_initial_pitch([]) == 0


class TestNoiseExporterGetFeatureMap:
    def test_feature_map_contains_all_required_keys(self) -> None:
        feature_map = NoiseExporter.get_feature_map([_noise(period=3, volume=10)], 3)
        assert FeatureKey.INITIAL_PITCH in feature_map
        assert FeatureKey.VOLUME in feature_map
        assert FeatureKey.ARPEGGIO in feature_map
        assert FeatureKey.DUTY_CYCLE in feature_map

    def test_arpeggio_is_relative_to_the_given_reference_modulo_num_periods(self) -> None:
        instructions = [
            _noise(period=2, volume=10),
            _noise(period=5, volume=8),
        ]
        feature_map = NoiseExporter.get_feature_map(instructions, 4)
        arpeggio = feature_map[FeatureKey.ARPEGGIO]
        assert int(arpeggio[0]) == (2 - 4) % NUM_PERIODS
        assert int(arpeggio[1]) == (5 - 4) % NUM_PERIODS

    def test_initial_pitch_is_the_given_reference(self) -> None:
        feature_map = NoiseExporter.get_feature_map([_noise(period=2, volume=10)], 9)
        assert feature_map[FeatureKey.INITIAL_PITCH] == 9

    def test_volume_array_dtype_is_int8(self) -> None:
        feature_map = NoiseExporter.get_feature_map([_noise()], 0)
        assert feature_map[FeatureKey.VOLUME].dtype == np.int8

    def test_arpeggio_dtype_is_int8(self) -> None:
        feature_map = NoiseExporter.get_feature_map([_noise()], 0)
        assert feature_map[FeatureKey.ARPEGGIO].dtype == np.int8

    def test_duty_cycle_dtype_is_int8(self) -> None:
        feature_map = NoiseExporter.get_feature_map([_noise()], 0)
        assert feature_map[FeatureKey.DUTY_CYCLE].dtype == np.int8


class TestNoiseExporterReconstruction:
    def test_features_dictionary_to_instruction_round_trip(self) -> None:
        initial_pitch = 3
        arpeggio = 2
        expected_period = (initial_pitch + arpeggio) % NUM_PERIODS
        dictionary = {"volume": 10, "period": arpeggio, "short": False}
        result = NoiseExporter._features_dictionary_to_instruction(
            dictionary,
            initial_pitch,
        )
        assert result.period == expected_period
        assert result.volume == 10
        assert result.short is False
        assert result.on is True

    def test_zero_volume_reconstructed_as_off(self) -> None:
        dictionary = {"volume": 0, "period": 0, "short": False}
        result = NoiseExporter._features_dictionary_to_instruction(dictionary, 0)
        assert result.on is False

    def test_short_mode_preserved_in_reconstruction(self) -> None:
        dictionary = {"volume": 8, "period": 0, "short": True}
        result = NoiseExporter._features_dictionary_to_instruction(dictionary, 0)
        assert result.short is True


class TestNoiseExporterTypeGetters:
    def test_get_instruction_type_returns_noise_instruction(self) -> None:
        assert NoiseExporter.get_instruction_type() is NoiseInstruction

    def test_get_generator_type_returns_noise_generator(self) -> None:
        assert NoiseExporter.get_generator_type() is NoiseGenerator
