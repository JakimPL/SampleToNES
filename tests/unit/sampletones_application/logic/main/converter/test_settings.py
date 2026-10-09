from typing import List

from sampletones_application.constants.output import OutputKind
from sampletones_application.logic.main.converter.settings import RunSettings
from sampletones_core.constants.algorithm import DEFAULT_STEMS_HIERARCHY_MODE
from sampletones_core.constants.enums import ChannelName, HierarchyMode
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from tests.suite.base import BaseTestSuite

TONES: List[ChannelName] = [ChannelName.PULSE1, ChannelName.PULSE2, ChannelName.TRIANGLE]


def _settings(channels: List[ChannelName]) -> RunSettings:
    return RunSettings(
        joining=StemSettings.covering(channels),
        output=OutputKind.PER_RECORDING,
        hierarchy_mode=DEFAULT_STEMS_HIERARCHY_MODE,
    )


class TestWhatARecordingJoinsWith(BaseTestSuite):
    def test_the_settings_a_recording_joins_with_are_the_readers_to_name(self) -> None:
        joining = StemSettings.covering([ChannelName.NOISE]).with_channel_cap(1)

        settings = _settings(TONES).with_joining(joining)

        assert settings.joining == joining

    def test_naming_them_leaves_the_shape_of_the_run(self) -> None:
        settings = _settings(TONES).with_output(OutputKind.MIXED)

        named = settings.with_joining(StemSettings.covering([ChannelName.NOISE]))

        assert (named.output, named.hierarchy_mode) == (settings.output, settings.hierarchy_mode)


class TestTheShapeOfTheRun(BaseTestSuite):
    def test_the_run_is_named_as_a_mix(self) -> None:
        assert _settings(TONES).with_output(OutputKind.MIXED).mixes is True

    def test_the_levels_take_turns_as_the_reader_asked(self) -> None:
        settings = _settings(TONES).with_hierarchy_mode(HierarchyMode.STRICT)

        assert settings.hierarchy_mode == HierarchyMode.STRICT
