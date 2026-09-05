from sampletones_application.logic.main.sources.slots import (
    BEND_SLOT,
    CHANNEL_SLOT,
    SETTINGS_SLOTS,
)
from sampletones_core.constants.enums import TONE_CHANNELS, ChannelName
from tests.unit.sampletones_application.logic.main.sources.factories import settings


class TestWhichChannelsASlotIsOfferedOn:
    """A choice reaches a reader only on the channels whose hardware answers it."""

    def test_a_channel_is_offered_on_every_channel(self) -> None:
        assert all(CHANNEL_SLOT.offers(channel_name) for channel_name in ChannelName.items())

    def test_a_bend_is_offered_on_the_channels_that_read_one(self) -> None:
        assert BEND_SLOT.channels_offered == TONE_CHANNELS
        assert not BEND_SLOT.offers(ChannelName.NOISE)


class TestSettlingTheChannelsARecordingOccupies:
    def test_a_channel_settled_on_joins_the_ones_held(self) -> None:
        settled = CHANNEL_SLOT.settled(settings(), ChannelName.NOISE, True)
        assert settled.channel_set == {ChannelName.PULSE1, ChannelName.NOISE}

    def test_a_channel_settled_off_leaves_the_ones_held(self) -> None:
        held = settings([ChannelName.PULSE1, ChannelName.NOISE])
        settled = CHANNEL_SLOT.settled(held, ChannelName.NOISE, False)
        assert settled.channel_set == {ChannelName.PULSE1}

    def test_the_channels_stand_in_the_order_the_application_names_them(self) -> None:
        held = settings([ChannelName.NOISE])
        settled = CHANNEL_SLOT.settled(held, ChannelName.PULSE1, True)
        assert settled.channels == [ChannelName.PULSE1, ChannelName.NOISE]

    def test_a_channel_settled_off_takes_the_bend_it_carried(self) -> None:
        held = settings([ChannelName.PULSE1, ChannelName.TRIANGLE], [ChannelName.TRIANGLE])
        settled = CHANNEL_SLOT.settled(held, ChannelName.TRIANGLE, False)
        assert settled.bends == []


class TestSettlingTheChannelsARecordingBends:
    def test_a_bend_settled_on_a_channel_held_stands(self) -> None:
        held = settings([ChannelName.PULSE1, ChannelName.TRIANGLE])
        settled = BEND_SLOT.settled(held, ChannelName.TRIANGLE, True)
        assert settled.bend_set == {ChannelName.TRIANGLE}

    def test_a_bend_reaches_only_a_channel_the_recording_occupies(self) -> None:
        settled = BEND_SLOT.settled(settings([ChannelName.PULSE1]), ChannelName.TRIANGLE, True)
        assert settled.bends == []

    def test_a_bend_reaches_only_a_channel_whose_hardware_reads_one(self) -> None:
        held = settings([ChannelName.PULSE1, ChannelName.NOISE])
        settled = BEND_SLOT.settled(held, ChannelName.NOISE, True)
        assert settled.bends == []

    def test_settling_a_bend_leaves_the_channels_as_they_stand(self) -> None:
        held = settings([ChannelName.PULSE1, ChannelName.TRIANGLE])
        settled = BEND_SLOT.settled(held, ChannelName.TRIANGLE, True)
        assert settled.channels == held.channels


class TestTheSlotsARecordingOffers:
    def test_every_slot_reads_and_settles_the_choice_it_names(self) -> None:
        for slot in SETTINGS_SLOTS:
            held = settings(list(TONE_CHANNELS))
            settled = slot.settled(held, ChannelName.TRIANGLE, True)
            assert slot.holds(settled, ChannelName.TRIANGLE)
            assert not slot.holds(slot.settled(settled, ChannelName.TRIANGLE, False), ChannelName.TRIANGLE)
