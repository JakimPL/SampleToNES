from typing import Final, Set

from tests.integration.sampletones_application.playback.breaks import STOP_WAITS, TAIL_ON_STOP, broken
from tests.integration.sampletones_application.playback.material import (
    REALTIME,
    SoundCase,
    Span,
    case,
    each,
    played_through,
    prepare,
    start,
    start_sounding,
)
from tests.integration.sampletones_application.playback.rig import Gate, PlaybackRig, Sound, from_write
from tests.suite.audio.machine import StreamCall
from tests.suite.audio.timeline import Drained
from tests.suite.base import BaseTestSuite

HELD_WRITE: Final[int] = 1


def _drained(rig: PlaybackRig) -> Set[int]:
    return {event.stream for event in rig.timeline.of(Drained)}


class TestStopReturnsAtOnce(BaseTestSuite):
    """Rule 6: Stop silences everything and returns at once, so the render thread waits on no device."""

    TestCase = SoundCase
    test_cases = tuple(case(sound, broken(STOP_WAITS)) for sound in Sound)

    @each(test_cases)
    def test_stop_returns_while_the_writer_is_held(self, rig: PlaybackRig, test_case: SoundCase) -> None:
        rig.shorten_deadlines()
        rig.expect_errors()
        gate: Gate[StreamCall] = Gate(holds=from_write(HELD_WRITE))
        rig.system.hooks.before_write = gate
        prepare(rig, test_case.sound, Span.LONG)
        start(rig, test_case.sound)
        gate.wait_for_arrival()

        rig.stop_all()
        waits = rig.waits
        gate.open()
        rig.settle()

        assert waits == []


class TestTail(BaseTestSuite):
    """Rule 6: a natural end plays the tail out, and a stop or a takeover cuts it."""

    TestCase = SoundCase
    test_cases = tuple(case(sound) for sound in Sound)
    stopped_cases = tuple(case(sound, broken(TAIL_ON_STOP)) for sound in Sound)

    @each(test_cases)
    def test_a_natural_end_plays_the_tail_out(self, rig: PlaybackRig, test_case: SoundCase) -> None:
        played_through(rig, test_case.sound)

        assert set(rig.timeline.streams()) == _drained(rig)

    @REALTIME
    @each(stopped_cases)
    def test_a_stop_cuts_the_tail(self, rig: PlaybackRig, test_case: SoundCase) -> None:
        start_sounding(rig, test_case.sound)

        rig.stop_all()
        rig.settle()

        assert rig.timeline.streams()
        assert not _drained(rig)

    @REALTIME
    @broken(TAIL_ON_STOP)
    def test_a_takeover_cuts_the_tail(self, rig: PlaybackRig) -> None:
        start_sounding(rig, Sound.RECONSTRUCTION)
        taken = rig.timeline.streams()[0]

        start_sounding(rig, Sound.SONG)
        rig.stop_all()
        rig.settle()

        assert taken not in _drained(rig)
