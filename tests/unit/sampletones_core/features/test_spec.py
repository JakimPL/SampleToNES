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
    generator_channel,
    supported_features,
    supports,
)
from sampletones_core.formats.famitracker.specification.sequences import (
    FEATURE_KEY_TO_SEQUENCE_KIND,
    SequenceKind,
)


def test_supported_features_follow_dimension_order() -> None:
    for generator_name in GeneratorName:
        offered = supported_features(generator_name)

        assert offered == [feature_key for feature_key in FEATURE_DIMENSION_ORDER if feature_key in offered]


def test_a_generator_offers_every_dimension_it_states_a_range_for() -> None:
    for generator_name in GeneratorName:
        offered = set(supported_features(generator_name))

        assert offered == {
            feature_key for feature_key in FEATURE_DIMENSION_ORDER if supports(generator_name, feature_key)
        }


def test_the_noise_channel_reads_no_bend() -> None:
    """Its sixteen periods have no finer grid, so a bend would state a resolution it lacks."""
    assert not supports(GeneratorName.NOISE, FeatureKey.PITCH)
    assert not supports(GeneratorName.NOISE, FeatureKey.HI_PITCH)


def test_the_tonal_channels_read_both_bend_dimensions() -> None:
    for generator_name in (GeneratorName.PULSE, GeneratorName.TRIANGLE):
        assert supports(generator_name, FeatureKey.PITCH)
        assert supports(generator_name, FeatureKey.HI_PITCH)


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


def test_a_generator_is_heard_on_the_first_channel_it_drives() -> None:
    assert generator_channel(GeneratorName.PULSE) is ChannelName.PULSE1
    assert generator_channel(GeneratorName.TRIANGLE) is ChannelName.TRIANGLE
    assert generator_channel(GeneratorName.NOISE) is ChannelName.NOISE


def test_every_generator_names_a_channel_that_reads_it_back() -> None:
    for generator_name in GeneratorName:
        assert CHANNEL_GENERATOR_KIND[generator_channel(generator_name)] is generator_name
