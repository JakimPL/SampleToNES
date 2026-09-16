from sampletones_core.constants.enums import ChannelName
from sampletones_tools.calibration.layout import CHANNEL_SEPARATOR, combination_name


class TestCombinationName:
    def test_one_channel_is_named_by_itself(self) -> None:
        assert combination_name([ChannelName.NOISE]) == ChannelName.NOISE.value

    def test_several_channels_are_joined_in_the_order_they_are_given(self) -> None:
        name = combination_name([ChannelName.PULSE1, ChannelName.TRIANGLE])

        assert name == f"{ChannelName.PULSE1.value}{CHANNEL_SEPARATOR}{ChannelName.TRIANGLE.value}"

    def test_every_combination_carries_its_own_name(self) -> None:
        channels = [ChannelName.PULSE1, ChannelName.TRIANGLE, ChannelName.NOISE]
        names = [combination_name(part) for part in ([channels[0]], channels[:2], channels)]

        assert len(set(names)) == len(names)
