from dataclasses import dataclass
from typing import FrozenSet

import pytest

from sampletones_application.view_model.sequencer.channels import SequencerChannelsViewModel
from sampletones_core.constants.enums import ChannelName
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

ALL_CHANNELS = frozenset(ChannelName.items())

PULSE1 = ChannelName.PULSE1
PULSE2 = ChannelName.PULSE2
TRIANGLE = ChannelName.TRIANGLE
NOISE = ChannelName.NOISE


class TestAllMuted(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class AllMutedCase(BaseRegularTestCase):
        muted: FrozenSet[ChannelName]
        expected: bool

    test_cases = (
        AllMutedCase(
            label="nothing silenced",
            muted=frozenset(),
            expected=False,
        ),
        AllMutedCase(
            label="one silenced",
            muted=frozenset({PULSE1}),
            expected=False,
        ),
        AllMutedCase(
            label="three silenced",
            muted=frozenset({PULSE1, PULSE2, NOISE}),
            expected=False,
        ),
        AllMutedCase(
            label="every channel silenced",
            muted=ALL_CHANNELS,
            expected=True,
        ),
    )

    @pytest.mark.parametrize("case", test_cases, ids=lambda case: case.label)
    def test_all_muted_reports_full_silence(self, case: AllMutedCase) -> None:
        view_model = SequencerChannelsViewModel(muted=case.muted)

        assert view_model.all_muted is case.expected


class TestAnyMuted(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class AllMutedCase(BaseRegularTestCase):
        muted: FrozenSet[ChannelName]
        expected: bool

    test_cases = (
        AllMutedCase(
            label="nothing silenced",
            muted=frozenset(),
            expected=False,
        ),
        AllMutedCase(
            label="one silenced",
            muted=frozenset({PULSE1}),
            expected=True,
        ),
        AllMutedCase(
            label="three silenced",
            muted=frozenset({PULSE1, PULSE2, NOISE}),
            expected=True,
        ),
        AllMutedCase(
            label="every channel silenced",
            muted=ALL_CHANNELS,
            expected=True,
        ),
    )

    @pytest.mark.parametrize("case", test_cases, ids=lambda case: case.label)
    def test_any_muted_reports_a_silenced_channel(
        self,
        case: AllMutedCase,
    ) -> None:
        view_model = SequencerChannelsViewModel(muted=case.muted)

        assert view_model.any_muted is case.expected

    def test_the_two_readings_agree_in_full_silence(self) -> None:
        view_model = SequencerChannelsViewModel(muted=ALL_CHANNELS)

        assert view_model.any_muted and view_model.all_muted


class TestIsSoloed:
    @pytest.mark.parametrize(
        "channel",
        ChannelName.items(),
        ids=lambda channel: channel.value,
    )
    def test_the_one_audible_channel_reads_as_soloed(
        self,
        channel: ChannelName,
    ) -> None:
        view_model = SequencerChannelsViewModel(muted=ALL_CHANNELS - {channel})

        soloed = {other for other in ChannelName.items() if view_model.is_soloed(other)}

        assert soloed == {channel}

    def test_no_channel_is_soloed_in_a_full_mix(self) -> None:
        view_model = SequencerChannelsViewModel(muted=frozenset())

        assert not any(view_model.is_soloed(channel) for channel in ChannelName.items())

    def test_no_channel_is_soloed_in_full_silence(self) -> None:
        view_model = SequencerChannelsViewModel(muted=ALL_CHANNELS)

        assert not any(view_model.is_soloed(channel) for channel in ChannelName.items())

    def test_two_audible_channels_leave_neither_soloed(self) -> None:
        view_model = SequencerChannelsViewModel(muted=frozenset({PULSE1, PULSE2}))

        assert not view_model.is_soloed(TRIANGLE)
        assert not view_model.is_soloed(NOISE)


class TestIsMuted:
    @pytest.mark.parametrize(
        "channel",
        ChannelName.items(),
        ids=lambda channel: channel.value,
    )
    def test_is_muted_reports_membership_of_the_mute_set(
        self,
        channel: ChannelName,
    ) -> None:
        view_model = SequencerChannelsViewModel(muted=frozenset({TRIANGLE, NOISE}))

        assert view_model.is_muted(channel) is (channel in {TRIANGLE, NOISE})

    def test_no_channel_is_muted_in_a_full_mix(self) -> None:
        view_model = SequencerChannelsViewModel(muted=frozenset())

        assert not any(view_model.is_muted(channel) for channel in ChannelName.items())
