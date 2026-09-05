from typing import List

from sampletones_application.constants.conversion import MIN_CHANNEL_CAP
from sampletones_application.constants.output import OutputKind
from sampletones_application.logic.main.converter.settings import RunSettings
from sampletones_core.constants.algorithm import DEFAULT_STEMS_HIERARCHY_MODE
from sampletones_core.constants.enums import ChannelName, HierarchyMode, bending_channels
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings

TONES: List[ChannelName] = [ChannelName.PULSE1, ChannelName.PULSE2, ChannelName.TRIANGLE]


def _settings(channels: List[ChannelName], channel_cap: int = 4) -> RunSettings:
    return RunSettings(
        joining=_joining(channels),
        output=OutputKind.PER_RECORDING,
        channel_cap=channel_cap,
        hierarchy_mode=DEFAULT_STEMS_HIERARCHY_MODE,
    )


def _joining(channels: List[ChannelName]) -> StemSettings:
    return StemSettings(channels=channels, bends=bending_channels(channels))


class TestTheChannelsARunHandsOut:
    def test_the_channels_a_recording_joins_with_are_what_the_run_enables(self) -> None:
        assert _settings(TONES).enabled_channels == frozenset(TONES)

    def test_narrowing_the_joining_channels_takes_the_bends_they_carried(self) -> None:
        narrowed = _settings(TONES).with_joining_channels(frozenset({ChannelName.PULSE1}))

        assert narrowed.joining.channels == [ChannelName.PULSE1]
        assert ChannelName.TRIANGLE not in narrowed.joining.bends


class TestTheCapARunHoldsTo:
    def test_a_cap_beyond_the_channels_there_are_is_held_to_them(self) -> None:
        settings = _settings(TONES).with_channel_cap(len(ChannelName) + 5)

        assert settings.effective_channel_cap == len(ChannelName)

    def test_a_cap_below_one_channel_is_refused(self) -> None:
        assert _settings(TONES).with_channel_cap(0).effective_channel_cap == MIN_CHANNEL_CAP

    def test_the_cap_stands_whatever_a_row_holds(self) -> None:
        """The cap bounds a frame, so it answers to the hardware rather than to one row."""
        settings = _settings(TONES).with_channel_cap(3).with_joining_channels(frozenset({ChannelName.PULSE1}))

        assert settings.effective_channel_cap == 3


class TestTheShapeOfTheRun:
    def test_the_run_is_named_as_a_mix(self) -> None:
        assert _settings(TONES).with_output(OutputKind.MIXED).mixes is True

    def test_the_levels_take_turns_as_the_reader_asked(self) -> None:
        settings = _settings(TONES).with_hierarchy_mode(HierarchyMode.STRICT)

        assert settings.hierarchy_mode == HierarchyMode.STRICT
