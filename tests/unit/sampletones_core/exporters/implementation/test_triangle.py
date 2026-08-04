import numpy as np

from sampletones_core.constants.enums import FeatureKey
from sampletones_core.constants.general import MAX_PITCH, MIN_PITCH
from sampletones_core.exporters.implementation.triangle import TriangleExporter
from sampletones_core.generators import TriangleGenerator
from sampletones_core.instructions.implementation.triangle import TriangleInstruction


def _tri(pitch: int = 60, volume: int = 15) -> TriangleInstruction:
    return TriangleInstruction(on=volume > 0, pitch=pitch)


def _off() -> TriangleInstruction:
    return TriangleInstruction(on=False, pitch=MIN_PITCH)


class TestTriangleExporterExtractData:
    def test_initial_pitch_from_first_on_instruction(self) -> None:
        initial_pitch, _, _ = TriangleExporter.extract_data([_tri(pitch=70)])
        assert initial_pitch == 70

    def test_all_off_instructions_initial_pitch_is_min_pitch(self) -> None:
        initial_pitch, _, _ = TriangleExporter.extract_data([_off(), _off()])
        assert initial_pitch == MIN_PITCH

    def test_off_instruction_produces_zero_volume(self) -> None:
        instructions = [_tri(pitch=60), _off()]
        _, _, volumes = TriangleExporter.extract_data(instructions)
        assert volumes[1] == 0

    def test_on_instruction_produces_nonzero_volume(self) -> None:
        from sampletones_core.constants.general import MAX_VOLUME

        _, _, volumes = TriangleExporter.extract_data([_tri(pitch=60)])
        assert volumes[0] == MAX_VOLUME

    def test_trailing_nonzero_volume_appends_extra_zero(self) -> None:
        _, _, volumes = TriangleExporter.extract_data([_tri(pitch=60)])
        assert volumes[-1] == 0
        assert len(volumes) == 2

    def test_off_instructions_before_on_get_backfilled(self) -> None:
        instructions = [_off(), _tri(pitch=55)]
        _, pitches, _ = TriangleExporter.extract_data(instructions)
        assert pitches[0] == 55

    def test_empty_instruction_list_returns_min_pitch(self) -> None:
        initial_pitch, pitches, volumes = TriangleExporter.extract_data([])
        assert initial_pitch == MIN_PITCH
        assert pitches == []
        assert volumes == []


class TestTriangleExporterDeriveInitialPitch:
    def test_reference_is_the_midpoint_of_the_contour(self) -> None:
        instructions = [_tri(pitch=60), _tri(pitch=72)]
        assert TriangleExporter.derive_initial_pitch(instructions) == 66

    def test_flat_contour_references_its_own_pitch(self) -> None:
        instructions = [_tri(pitch=60), _tri(pitch=60)]
        assert TriangleExporter.derive_initial_pitch(instructions) == 60

    def test_empty_instruction_list_references_min_pitch(self) -> None:
        assert TriangleExporter.derive_initial_pitch([]) == MIN_PITCH


class TestTriangleExporterGetFeatureMap:
    def test_feature_map_contains_required_keys(self) -> None:
        feature_map = TriangleExporter.get_feature_map([_tri(pitch=60)], 60)
        assert FeatureKey.INITIAL_PITCH in feature_map
        assert FeatureKey.VOLUME in feature_map
        assert FeatureKey.ARPEGGIO in feature_map

    def test_arpeggio_is_relative_to_the_given_reference(self) -> None:
        instructions = [_tri(pitch=60), _tri(pitch=65)]
        feature_map = TriangleExporter.get_feature_map(instructions, 60)
        arpeggio = feature_map[FeatureKey.ARPEGGIO]
        assert int(arpeggio[0]) == 0
        assert int(arpeggio[1]) == 5

    def test_initial_pitch_is_the_given_reference(self) -> None:
        feature_map = TriangleExporter.get_feature_map([_tri(pitch=60)], 55)
        assert feature_map[FeatureKey.INITIAL_PITCH] == 55
        assert int(feature_map[FeatureKey.ARPEGGIO][0]) == 5

    def test_volume_dtype_is_int8(self) -> None:
        feature_map = TriangleExporter.get_feature_map([_tri()], 60)
        assert feature_map[FeatureKey.VOLUME].dtype == np.int8

    def test_arpeggio_dtype_is_int8(self) -> None:
        feature_map = TriangleExporter.get_feature_map([_tri()], 60)
        assert feature_map[FeatureKey.ARPEGGIO].dtype == np.int8


class TestTriangleExporterReconstruction:
    def test_valid_pitch_round_trips(self) -> None:
        initial_pitch = 50
        arpeggio = 10
        dictionary = {"pitch": arpeggio, "volume": 15}
        result = TriangleExporter._features_dictionary_to_instruction(
            dictionary,
            initial_pitch,
        )
        assert result.pitch == initial_pitch + arpeggio
        assert result.on is True

    def test_invalid_pitch_above_max_returns_null_instruction(self) -> None:
        initial_pitch = MAX_PITCH
        arpeggio = 10
        dictionary = {"pitch": arpeggio, "volume": 10}
        result = TriangleExporter._features_dictionary_to_instruction(
            dictionary,
            initial_pitch,
        )
        assert result.on is False
        assert result.pitch == MIN_PITCH

    def test_invalid_pitch_below_min_returns_null_instruction(self) -> None:
        initial_pitch = MIN_PITCH
        arpeggio = -10
        dictionary = {"pitch": arpeggio, "volume": 10}
        result = TriangleExporter._features_dictionary_to_instruction(
            dictionary,
            initial_pitch,
        )
        assert result.on is False

    def test_zero_volume_reconstructed_as_off(self) -> None:
        dictionary = {"pitch": 0, "volume": 0}
        result = TriangleExporter._features_dictionary_to_instruction(dictionary, 60)
        assert result.on is False


class TestTriangleExporterTypeGetters:
    def test_get_instruction_type_returns_triangle_instruction(self) -> None:
        assert TriangleExporter.get_instruction_type() is TriangleInstruction

    def test_get_generator_type_returns_triangle_generator(self) -> None:
        assert TriangleExporter.get_generator_type() is TriangleGenerator
