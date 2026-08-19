from sampletones_core.constants.enums import (
    ChannelName,
    FeatureKey,
    GeneratorName,
)
from sampletones_core.exporters.implementation.noise import NoiseExporter
from sampletones_core.exporters.implementation.pulse import PulseExporter
from sampletones_core.exporters.implementation.triangle import TriangleExporter
from sampletones_core.features import (
    CHANNEL_GENERATOR_KIND,
    FEATURE_DIMENSION_ORDER,
    feature_range,
    supported_features,
    supports,
)
from sampletones_core.formats.famitracker.specification.sequences import (
    FEATURE_KEY_TO_SEQUENCE_KIND,
    SequenceKind,
)


def test_supported_features_follow_dimension_order() -> None:
    assert supported_features(GeneratorName.PULSE) == [
        FeatureKey.VOLUME,
        FeatureKey.ARPEGGIO,
        FeatureKey.DUTY_CYCLE,
    ]
    assert supported_features(GeneratorName.TRIANGLE) == [
        FeatureKey.VOLUME,
        FeatureKey.ARPEGGIO,
    ]
    assert supported_features(GeneratorName.NOISE) == [
        FeatureKey.VOLUME,
        FeatureKey.ARPEGGIO,
        FeatureKey.DUTY_CYCLE,
    ]


def test_feature_ranges_match_expected_channel_domains() -> None:
    assert feature_range(GeneratorName.PULSE, FeatureKey.DUTY_CYCLE) == feature_range(
        CHANNEL_GENERATOR_KIND[ChannelName.PULSE1],
        FeatureKey.DUTY_CYCLE,
    )
    assert feature_range(GeneratorName.NOISE, FeatureKey.DUTY_CYCLE).maximum == 1
    assert feature_range(GeneratorName.NOISE, FeatureKey.ARPEGGIO).minimum == 0
    assert feature_range(GeneratorName.NOISE, FeatureKey.ARPEGGIO).maximum == 15


def test_supports_reports_triangle_lacks_duty_cycle() -> None:
    assert supports(GeneratorName.TRIANGLE, FeatureKey.VOLUME)
    assert not supports(GeneratorName.TRIANGLE, FeatureKey.DUTY_CYCLE)


def test_supported_features_match_exporter_attribute_maps() -> None:
    assert tuple(supported_features(GeneratorName.PULSE)) == tuple(PulseExporter._ATTRIBUTE_MAP)
    assert tuple(supported_features(GeneratorName.TRIANGLE)) == tuple(TriangleExporter._ATTRIBUTE_MAP)
    assert tuple(supported_features(GeneratorName.NOISE)) == tuple(NoiseExporter._ATTRIBUTE_MAP)


def test_feature_dimension_order_matches_famitracker_sequence_slots() -> None:
    expected = [
        SequenceKind.VOLUME,
        SequenceKind.ARPEGGIO,
        SequenceKind.PITCH,
        SequenceKind.HI_PITCH,
        SequenceKind.DUTY,
    ]
    assert [FEATURE_KEY_TO_SEQUENCE_KIND[key] for key in FEATURE_DIMENSION_ORDER] == expected
