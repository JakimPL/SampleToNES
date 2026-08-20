from sampletones_core.constants.enums import ChannelName, abbreviate_channel_names


class TestAbbreviateChannelNames:
    def test_single_generator_produces_its_abbreviation(self) -> None:
        assert abbreviate_channel_names([ChannelName.PULSE1]) == "P"

    def test_multiple_generators_concatenates_in_order(self) -> None:
        assert "PTN" == abbreviate_channel_names(
            [
                ChannelName.PULSE1,
                ChannelName.TRIANGLE,
                ChannelName.NOISE,
            ]
        )
