from sampletones_core.constants.enums import (
    FeatureKey,
    GeneratorName,
    LibraryGeneratorName,
)
from sampletones_core.exporters.implementation.noise import NoiseExporter
from sampletones_core.exporters.implementation.pulse import PulseExporter
from sampletones_core.exporters.implementation.triangle import TriangleExporter
from sampletones_core.features import (
    FEATURE_DIMENSION_ORDER,
    GENERATOR_KIND,
    feature_range,
    supported_features,
    supports,
)
from sampletones_core.formats.famitracker.specification.sequences import (
    FEATURE_KEY_TO_SEQUENCE_KIND,
    SequenceKind,
)


def test_supported_features_follow_dimension_order() -> None:
    assert supported_features(LibraryGeneratorName.PULSE) == [
        FeatureKey.VOLUME,
        FeatureKey.ARPEGGIO,
        FeatureKey.DUTY_CYCLE,
    ]
    assert supported_features(LibraryGeneratorName.TRIANGLE) == [
        FeatureKey.VOLUME,
        FeatureKey.ARPEGGIO,
    ]
    assert supported_features(LibraryGeneratorName.NOISE) == [
        FeatureKey.VOLUME,
        FeatureKey.ARPEGGIO,
        FeatureKey.DUTY_CYCLE,
    ]


def test_feature_ranges_match_expected_channel_domains() -> None:
    assert feature_range(LibraryGeneratorName.PULSE, FeatureKey.DUTY_CYCLE) == feature_range(
        GENERATOR_KIND[GeneratorName.PULSE1],
        FeatureKey.DUTY_CYCLE,
    )
    assert feature_range(LibraryGeneratorName.NOISE, FeatureKey.DUTY_CYCLE).maximum == 1
    assert feature_range(LibraryGeneratorName.NOISE, FeatureKey.ARPEGGIO).minimum == 0
    assert feature_range(LibraryGeneratorName.NOISE, FeatureKey.ARPEGGIO).maximum == 15


def test_supports_reports_triangle_lacks_duty_cycle() -> None:
    assert supports(LibraryGeneratorName.TRIANGLE, FeatureKey.VOLUME)
    assert not supports(LibraryGeneratorName.TRIANGLE, FeatureKey.DUTY_CYCLE)


def test_supported_features_match_exporter_attribute_maps() -> None:
    assert tuple(supported_features(LibraryGeneratorName.PULSE)) == tuple(PulseExporter._ATTRIBUTE_MAP)
    assert tuple(supported_features(LibraryGeneratorName.TRIANGLE)) == tuple(TriangleExporter._ATTRIBUTE_MAP)
    assert tuple(supported_features(LibraryGeneratorName.NOISE)) == tuple(NoiseExporter._ATTRIBUTE_MAP)


def test_feature_dimension_order_matches_famitracker_sequence_slots() -> None:
    expected = [
        SequenceKind.VOLUME,
        SequenceKind.ARPEGGIO,
        SequenceKind.PITCH,
        SequenceKind.HI_PITCH,
        SequenceKind.DUTY,
    ]
    assert [FEATURE_KEY_TO_SEQUENCE_KIND[key] for key in FEATURE_DIMENSION_ORDER] == expected
