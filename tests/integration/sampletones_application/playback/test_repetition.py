from typing import Final, List

import numpy as np

from tests.integration.sampletones_application.playback.material import (
    REALTIME,
    SHORT,
    SoundCase,
    Span,
    case,
    each,
    prepare,
    ramp_material,
    start,
    start_sounding,
)
from tests.integration.sampletones_application.playback.rig import BUFFERS, EndCause, PlaybackRig, Sound
from tests.suite.base import BaseTestSuite

STORM: Final[int] = 20


@REALTIME
class TestStorms(BaseTestSuite):
    """Rules 2 and 3: a sound started and stopped over and over keeps one stream open at a time, and ends each time."""

    TestCase = SoundCase
    test_cases = tuple(case(sound) for sound in Sound)

    @each(test_cases)
    def test_a_storm_keeps_one_stream_open_at_a_time(self, rig: PlaybackRig, test_case: SoundCase) -> None:
        prepare(rig, test_case.sound, Span.LONG)
        for _ in range(STORM):
            start(rig, test_case.sound)
            rig.stop_all()

        rig.settle()

        assert rig.timeline.most_streams_open() <= 1
        assert not rig.timeline.violations()

    @each(test_cases)
    def test_a_storm_ends_every_playback_once(self, rig: PlaybackRig, test_case: SoundCase) -> None:
        prepare(rig, test_case.sound, Span.LONG)
        for _ in range(STORM):
            start(rig, test_case.sound)
            rig.stop_all()

        rig.settle()

        assert len(rig.ends(test_case.sound)) == STORM


class TestOverItself(BaseTestSuite):
    """Rule 2: a sound played again while it plays starts over on a stream opened once the first has closed.

    A key played live while keys sound joins the playback holding the output, so it plays on that stream.
    """

    TestCase = SoundCase
    test_cases = tuple(case(sound) for sound in Sound if sound is not Sound.KEYS)

    @REALTIME
    @each(test_cases)
    def test_playing_over_itself_starts_over(self, rig: PlaybackRig, test_case: SoundCase) -> None:
        start_sounding(rig, test_case.sound)

        start_sounding(rig, test_case.sound)
        rig.stop_all()
        rig.settle()

        assert len(rig.timeline.streams()) == 2
        assert rig.timeline.most_streams_open() == 1
        if ramp_material(test_case.sound):
            assert list(rig.written()).count(0) == 2

    @REALTIME
    def test_a_key_played_while_keys_sound_plays_on_their_stream(self, rig: PlaybackRig) -> None:
        start_sounding(rig, Sound.KEYS)

        start_sounding(rig, Sound.KEYS)
        rig.stop_all()
        rig.settle()

        assert len(rig.timeline.streams()) == 1
        assert rig.causes(Sound.KEYS) == [EndCause.STOPPED]


class TestEndHandler(BaseTestSuite):
    """Rule 3: an owner starting a new playback as it hears the end of one hears the new one whole."""

    TestCase = SoundCase
    test_cases = (
        case(Sound.RECONSTRUCTION),
        case(Sound.INSTRUCTION),
        case(Sound.SONG),
    )

    @each(test_cases)
    def test_a_playback_started_from_an_end_report_plays_whole(self, rig: PlaybackRig, test_case: SoundCase) -> None:
        replays: List[bool] = []

        def replay() -> None:
            if not replays:
                replays.append(True)
                start(rig, test_case.sound)

        rig.on_end(test_case.sound, replay)
        prepare(rig, test_case.sound, Span.SHORT)
        length = SHORT if test_case.sound in BUFFERS else rig.song.length
        start(rig, test_case.sound)
        rig.wait_for(lambda: len(rig.ends(test_case.sound)) >= 2, what="the second playback's end")
        rig.settle()

        np.testing.assert_array_equal(rig.written(), np.concatenate([np.arange(length), np.arange(length)]))
