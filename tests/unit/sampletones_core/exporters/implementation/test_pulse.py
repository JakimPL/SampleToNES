import numpy as np

from sampletones_core.constants.enums import FeatureKey
from sampletones_core.constants.general import MAX_PITCH, MIN_PITCH
from sampletones_core.exporters.implementation.pulse import PulseExporter
from sampletones_core.generators import PulseGenerator
from sampletones_core.instructions.implementation.pulse import PulseInstruction


def _pulse(pitch: int = 60, volume: int = 8, duty_cycle: int = 0) -> PulseInstruction:
    return PulseInstruction(on=volume > 0, pitch=pitch, volume=volume, duty_cycle=duty_cycle)


def _off() -> PulseInstruction:
    return PulseInstruction(on=False, pitch=MIN_PITCH, volume=0, duty_cycle=0)


class TestPulseExporterExtractData:
    def test_initial_pitch_from_first_on_instruction(self) -> None:
        initial_pitch, _, _, _ = PulseExporter.extract_data([_pulse(pitch=70)])
        assert initial_pitch == 70

    def test_all_off_instructions_initial_pitch_is_min_pitch(self) -> None:
        initial_pitch, _, _, _ = PulseExporter.extract_data([_off(), _off()])
        assert initial_pitch == MIN_PITCH

    def test_off_instruction_produces_zero_volume(self) -> None:
        _, _, volumes, _ = PulseExporter.extract_data([_pulse(pitch=60), _off()])
        assert volumes[1] == 0

    def test_on_instruction_carries_its_volume(self) -> None:
        _, _, volumes, _ = PulseExporter.extract_data([_pulse(pitch=60, volume=12)])
        assert volumes[0] == 12

    def test_trailing_nonzero_volume_appends_extra_zero(self) -> None:
        _, _, volumes, _ = PulseExporter.extract_data([_pulse(pitch=60)])
        assert volumes[-1] == 0
        assert len(volumes) == 2

    def test_off_instructions_before_on_get_backfilled(self) -> None:
        _, pitches, _, _ = PulseExporter.extract_data([_off(), _pulse(pitch=55)])
        assert pitches[0] == 55

    def test_duty_cycle_tracks_the_instruction(self) -> None:
        _, _, _, duty_cycles = PulseExporter.extract_data([_pulse(pitch=60, duty_cycle=2)])
        assert duty_cycles[0] == 2

    def test_empty_instruction_list_returns_min_pitch(self) -> None:
        initial_pitch, pitches, volumes, duty_cycles = PulseExporter.extract_data([])
        assert initial_pitch == MIN_PITCH
        assert pitches == []
        assert volumes == []
        assert duty_cycles == []


class TestPulseExporterDeriveInitialPitch:
    def test_reference_is_the_midpoint_of_the_contour(self) -> None:
        instructions = [_pulse(pitch=60), _pulse(pitch=72)]
        assert PulseExporter.derive_initial_pitch(instructions) == 66

    def test_flat_contour_references_its_own_pitch(self) -> None:
        instructions = [_pulse(pitch=60), _pulse(pitch=60)]
        assert PulseExporter.derive_initial_pitch(instructions) == 60

    def test_empty_instruction_list_references_min_pitch(self) -> None:
        assert PulseExporter.derive_initial_pitch([]) == MIN_PITCH


class TestPulseExporterGetFeatureMap:
    def test_feature_map_contains_required_keys(self) -> None:
        feature_map = PulseExporter.get_feature_map([_pulse(pitch=60)], 60)
        assert FeatureKey.INITIAL_PITCH in feature_map
        assert FeatureKey.VOLUME in feature_map
        assert FeatureKey.ARPEGGIO in feature_map
        assert FeatureKey.DUTY_CYCLE in feature_map

    def test_arpeggio_is_relative_to_the_given_reference(self) -> None:
        instructions = [_pulse(pitch=60), _pulse(pitch=65)]
        feature_map = PulseExporter.get_feature_map(instructions, 60)
        arpeggio = feature_map[FeatureKey.ARPEGGIO]
        assert int(arpeggio[0]) == 0
        assert int(arpeggio[1]) == 5

    def test_initial_pitch_is_the_given_reference(self) -> None:
        feature_map = PulseExporter.get_feature_map([_pulse(pitch=60)], 55)
        assert feature_map[FeatureKey.INITIAL_PITCH] == 55
        assert int(feature_map[FeatureKey.ARPEGGIO][0]) == 5

    def test_volume_dtype_is_int8(self) -> None:
        feature_map = PulseExporter.get_feature_map([_pulse()], 60)
        assert feature_map[FeatureKey.VOLUME].dtype == np.int8

    def test_arpeggio_dtype_is_int8(self) -> None:
        feature_map = PulseExporter.get_feature_map([_pulse()], 60)
        assert feature_map[FeatureKey.ARPEGGIO].dtype == np.int8

    def test_duty_cycle_dtype_is_int8(self) -> None:
        feature_map = PulseExporter.get_feature_map([_pulse()], 60)
        assert feature_map[FeatureKey.DUTY_CYCLE].dtype == np.int8


class TestPulseExporterReconstruction:
    def test_valid_pitch_round_trips(self) -> None:
        initial_pitch = 50
        arpeggio = 10
        dictionary = {"pitch": arpeggio, "volume": 8, "duty_cycle": 1}
        result = PulseExporter._features_dictionary_to_instruction(dictionary, initial_pitch)
        assert result.pitch == initial_pitch + arpeggio
        assert result.volume == 8
        assert result.duty_cycle == 1
        assert result.on is True

    def test_invalid_pitch_above_max_returns_null_instruction(self) -> None:
        dictionary = {"pitch": 10, "volume": 8, "duty_cycle": 0}
        result = PulseExporter._features_dictionary_to_instruction(dictionary, MAX_PITCH)
        assert result.on is False

    def test_invalid_pitch_below_min_returns_null_instruction(self) -> None:
        dictionary = {"pitch": -10, "volume": 8, "duty_cycle": 0}
        result = PulseExporter._features_dictionary_to_instruction(dictionary, MIN_PITCH)
        assert result.on is False

    def test_zero_volume_reconstructed_as_off(self) -> None:
        dictionary = {"pitch": 0, "volume": 0, "duty_cycle": 0}
        result = PulseExporter._features_dictionary_to_instruction(dictionary, 60)
        assert result.on is False


class TestPulseExporterTypeGetters:
    def test_get_instruction_type_returns_pulse_instruction(self) -> None:
        assert PulseExporter.get_instruction_type() is PulseInstruction

    def test_get_generator_type_returns_pulse_generator(self) -> None:
        assert PulseExporter.get_generator_type() is PulseGenerator
