from dataclasses import dataclass
from typing import Dict, List, Optional, Type

import pytest
from pydantic import ValidationError

from sampletones_core.constants.algorithm import (
    ALL_STEMS_CHANNEL_CAP,
    MAX_DRIVE,
    MIN_DRIVE,
    MIN_STEMS_CHANNEL_CAP,
    UNIT_DRIVE,
)
from sampletones_core.constants.enums import TONE_CHANNELS, ChannelName, bending_channels
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

PUSHED: float = 2.5
TWO_CHANNELS: List[ChannelName] = [ChannelName.PULSE1, ChannelName.TRIANGLE]


class TestTheBendsASettingsHolds(BaseTestSuite):
    """A bend names a channel the recording occupies and whose hardware loads a divider."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Optional[Type[Exception]]
        channels: List[ChannelName]
        bends: List[ChannelName]

    test_cases = (
        TestCase(
            label="bending_nothing",
            channels=[ChannelName.PULSE1, ChannelName.NOISE],
            bends=[],
            expected=None,
        ),
        TestCase(
            label="bending_a_channel_it_occupies",
            channels=[ChannelName.PULSE1, ChannelName.TRIANGLE],
            bends=[ChannelName.TRIANGLE],
            expected=None,
        ),
        TestCase(
            label="bending_every_tone_channel_it_occupies",
            channels=list(sorted(TONE_CHANNELS)),
            bends=list(sorted(TONE_CHANNELS)),
            expected=None,
        ),
        TestCase(
            label="bending_a_channel_it_leaves_out",
            channels=[ChannelName.PULSE1],
            bends=[ChannelName.TRIANGLE],
            expected=ValidationError,
        ),
        TestCase(
            label="bending_the_noise_channel",
            channels=[ChannelName.NOISE],
            bends=[ChannelName.NOISE],
            expected=ValidationError,
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_settings_are_held_to_their_bends(self, test_case: TestCase) -> None:
        if test_case.expected is None:
            settings = StemSettings(channels=test_case.channels, bends=test_case.bends)
            assert settings.bends == test_case.bends
            return

        with pytest.raises(test_case.expected):
            StemSettings(channels=test_case.channels, bends=test_case.bends)


class TestTheSetsSettingsAnswerWith:
    """The membership tests an assignment and the refinement each read once per frame."""

    def test_the_channel_set_holds_every_channel_occupied(self) -> None:
        settings = StemSettings(
            channels=[ChannelName.PULSE1, ChannelName.NOISE],
            bends=[ChannelName.PULSE1],
        )
        assert settings.channel_set == frozenset({ChannelName.PULSE1, ChannelName.NOISE})

    def test_the_bend_set_holds_every_channel_bent(self) -> None:
        settings = StemSettings(
            channels=[ChannelName.PULSE1, ChannelName.TRIANGLE],
            bends=[ChannelName.TRIANGLE],
        )
        assert settings.bend_set == frozenset({ChannelName.TRIANGLE})


class TestTheDrivesASettingsHolds(BaseTestSuite):
    """A drive stands on every channel the recording occupies, at unit where none was stated."""

    def test_channels_stated_without_a_drive_play_at_unit(self) -> None:
        settings = StemSettings(channels=TWO_CHANNELS, bends=[])
        assert settings.drives == {channel_name: UNIT_DRIVE for channel_name in TWO_CHANNELS}

    def test_a_drive_stated_stands_beside_the_unit_ones(self) -> None:
        settings = StemSettings(channels=TWO_CHANNELS, bends=[], drives={ChannelName.PULSE1: PUSHED})
        assert settings.drives == {ChannelName.PULSE1: PUSHED, ChannelName.TRIANGLE: UNIT_DRIVE}

    def test_a_drive_read_from_a_written_form_keys_by_channel(self) -> None:
        settings = StemSettings.model_validate(
            {"channels": ["pulse1", "triangle"], "bends": [], "drives": {"pulse1": PUSHED}}
        )
        assert settings.drives == {ChannelName.PULSE1: PUSHED, ChannelName.TRIANGLE: UNIT_DRIVE}

    def test_a_drive_on_a_channel_left_out_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="occupies"):
            StemSettings(channels=[ChannelName.PULSE1], bends=[], drives={ChannelName.NOISE: PUSHED})

    @pytest.mark.parametrize("drive", (MIN_DRIVE / 2, MAX_DRIVE * 2), ids=("below_the_floor", "above_the_ceiling"))
    def test_a_drive_outside_the_bounds_is_refused(self, drive: float) -> None:
        with pytest.raises(ValidationError, match="outside"):
            StemSettings(channels=[ChannelName.PULSE1], bends=[], drives={ChannelName.PULSE1: drive})

    def test_the_bounds_themselves_are_drives(self) -> None:
        settings = StemSettings(
            channels=TWO_CHANNELS,
            bends=[],
            drives={ChannelName.PULSE1: MIN_DRIVE, ChannelName.TRIANGLE: MAX_DRIVE},
        )
        assert settings.drives == {ChannelName.PULSE1: MIN_DRIVE, ChannelName.TRIANGLE: MAX_DRIVE}


class TestTheCountASettingsHolds(BaseTestSuite):
    """The count is the reader's choice within the channels the hardware has, whatever channels are held."""

    def test_a_recording_sounds_every_channel_at_once_until_told_otherwise(self) -> None:
        assert StemSettings(channels=[ChannelName.PULSE1], bends=[]).channel_cap == ALL_STEMS_CHANNEL_CAP

    @pytest.mark.parametrize(
        "channel_cap",
        (MIN_STEMS_CHANNEL_CAP - 1, ALL_STEMS_CHANNEL_CAP + 1),
        ids=("below_one", "beyond_the_channels_there_are"),
    )
    def test_a_count_outside_the_channels_there_are_is_refused(self, channel_cap: int) -> None:
        with pytest.raises(ValidationError):
            StemSettings(channels=[ChannelName.PULSE1], bends=[], channel_cap=channel_cap)

    def test_a_count_above_the_channels_held_stands(self) -> None:
        settings = StemSettings(channels=[ChannelName.PULSE1], bends=[], channel_cap=ALL_STEMS_CHANNEL_CAP)
        assert settings.channel_cap == ALL_STEMS_CHANNEL_CAP


class TestTheUsualSettings(BaseTestSuite):
    """What a recording is converted with until a reader says otherwise."""

    def test_covering_bends_every_tone_channel_at_unit_drive_all_at_once(self) -> None:
        channels = [ChannelName.PULSE1, ChannelName.TRIANGLE, ChannelName.NOISE]

        settings = StemSettings.covering(channels)

        assert settings.channels == channels
        assert settings.bends == bending_channels(channels)
        assert settings.drives == {channel_name: UNIT_DRIVE for channel_name in channels}
        assert settings.channel_cap == ALL_STEMS_CHANNEL_CAP


class TestRewritingTheChannels(BaseTestSuite):
    """Narrowing the channels narrows what belongs to them; a channel newly held plays at unit."""

    def test_a_channel_kept_keeps_its_drive_and_bend(self) -> None:
        settings = StemSettings.covering(TWO_CHANNELS).with_drive(ChannelName.PULSE1, PUSHED)

        rewritten = settings.with_channels({ChannelName.PULSE1})

        assert rewritten.channels == [ChannelName.PULSE1]
        assert rewritten.bends == [ChannelName.PULSE1]
        assert rewritten.drives == {ChannelName.PULSE1: PUSHED}

    def test_a_channel_newly_held_plays_at_unit_and_bends_nothing(self) -> None:
        settings = StemSettings.covering([ChannelName.PULSE1]).with_drive(ChannelName.PULSE1, PUSHED)

        rewritten = settings.with_channels({ChannelName.PULSE1, ChannelName.TRIANGLE})

        assert rewritten.channels == TWO_CHANNELS
        assert rewritten.bends == [ChannelName.PULSE1]
        assert rewritten.drives == {ChannelName.PULSE1: PUSHED, ChannelName.TRIANGLE: UNIT_DRIVE}

    def test_the_count_stays_the_readers_choice(self) -> None:
        settings = StemSettings.covering(TWO_CHANNELS).with_channel_cap(MIN_STEMS_CHANNEL_CAP)

        assert settings.with_channels({ChannelName.NOISE}).channel_cap == MIN_STEMS_CHANNEL_CAP

    def test_the_channels_stand_in_the_order_the_application_names_them(self) -> None:
        rewritten = StemSettings.covering([ChannelName.NOISE]).with_channels({ChannelName.NOISE, ChannelName.PULSE1})

        assert rewritten.channels == [ChannelName.PULSE1, ChannelName.NOISE]


class TestRewritingTheOtherChoices(BaseTestSuite):
    def test_a_bend_reaches_only_an_occupied_tone_channel(self) -> None:
        settings = StemSettings.covering([ChannelName.PULSE1, ChannelName.NOISE]).with_drive(ChannelName.NOISE, PUSHED)

        rewritten = settings.with_bends({ChannelName.PULSE1, ChannelName.TRIANGLE, ChannelName.NOISE})

        assert rewritten.bends == [ChannelName.PULSE1]
        assert rewritten.drives == settings.drives
        assert rewritten.channel_cap == settings.channel_cap

    def test_a_drive_lands_on_the_channel_named(self) -> None:
        settings = StemSettings.covering(TWO_CHANNELS).with_drive(ChannelName.TRIANGLE, PUSHED)

        assert settings.drives == {ChannelName.PULSE1: UNIT_DRIVE, ChannelName.TRIANGLE: PUSHED}

    def test_a_drive_on_a_channel_left_out_is_refused(self) -> None:
        with pytest.raises(ValueError, match="unoccupied"):
            StemSettings.covering([ChannelName.PULSE1]).with_drive(ChannelName.NOISE, PUSHED)

    def test_a_drive_outside_the_bounds_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="outside"):
            StemSettings.covering([ChannelName.PULSE1]).with_drive(ChannelName.PULSE1, MAX_DRIVE * 2)

    def test_a_count_lands_as_stated(self) -> None:
        assert StemSettings.covering(TWO_CHANNELS).with_channel_cap(2).channel_cap == 2

    def test_a_count_outside_the_channels_there_are_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            StemSettings.covering(TWO_CHANNELS).with_channel_cap(ALL_STEMS_CHANNEL_CAP + 1)


class TestTheWrittenForm(BaseTestSuite):
    """The settings come back from their written form as they went in, drives and count included."""

    def test_settings_survive_a_round_trip(self) -> None:
        drives: Dict[ChannelName, float] = {ChannelName.PULSE1: PUSHED, ChannelName.TRIANGLE: MIN_DRIVE}
        settings = StemSettings(
            channels=TWO_CHANNELS,
            bends=[ChannelName.TRIANGLE],
            drives=drives,
            channel_cap=MIN_STEMS_CHANNEL_CAP,
        )

        assert StemSettings.deserialize(settings.serialize()) == settings
