from tests.integration.sampletones_application.playback.material import (
    HEADPHONES_INDEX,
    HEADPHONES_RATE,
    REALTIME,
    SoundCase,
    case,
    each,
    start_sounding,
)
from tests.integration.sampletones_application.playback.rig import PlaybackRig, Sound
from tests.suite.audio.timeline import Opened
from tests.suite.base import BaseTestSuite


@REALTIME
class TestDeviceChanges(BaseTestSuite):
    """Rule 2: a device change or a refresh while a sound plays leaves one stream open, and the next sound plays."""

    TestCase = SoundCase
    test_cases = tuple(case(sound) for sound in Sound)

    @each(test_cases)
    def test_a_device_change_mid_sound_keeps_one_stream_open(self, rig: PlaybackRig, test_case: SoundCase) -> None:
        start_sounding(rig, test_case.sound)

        rig.change_device(HEADPHONES_INDEX, sample_rate=HEADPHONES_RATE)
        start_sounding(rig, test_case.sound)
        rig.stop_all()
        rig.settle()

        assert rig.told == []
        assert rig.timeline.most_streams_open() == 1
        assert rig.timeline.of(Opened)[-1].device == HEADPHONES_INDEX

    @each(test_cases)
    def test_a_refresh_mid_sound_keeps_one_stream_open(self, rig: PlaybackRig, test_case: SoundCase) -> None:
        start_sounding(rig, test_case.sound)

        rig.refresh()
        start_sounding(rig, test_case.sound)
        rig.stop_all()
        rig.settle()

        assert rig.told == []
        assert rig.timeline.most_streams_open() == 1
        assert len(rig.system.drivers) == 2
