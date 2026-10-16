from typing import Final

from sampletones_core.project.song_position import SongPosition
from tests.integration.sampletones_application.playback.material import (
    REALTIME,
    SoundCase,
    Span,
    case,
    each,
    prepare,
    start,
    start_sounding,
)
from tests.integration.sampletones_application.playback.rig import (
    ROW_SECONDS,
    SOURCES,
    Gate,
    HeldRow,
    PlaybackRig,
    Sound,
    every_call,
    from_write,
)
from tests.suite.audio.machine import OpenCall, StreamCall
from tests.suite.audio.timeline import Terminated
from tests.suite.base import BaseTestSuite

HELD_WRITE: Final[int] = 2
STARVED_ROW: Final[SongPosition] = SongPosition(order_position=0, row_index=2)


def _terminated(rig: PlaybackRig) -> bool:
    return bool(rig.timeline.of(Terminated))


@REALTIME
class TestQuitWhileSounding(BaseTestSuite):
    """Rule 8: quitting while a sound plays or stands paused ends every audio thread and closes every stream."""

    TestCase = SoundCase
    test_cases = tuple(case(sound) for sound in Sound)
    source_cases = tuple(case(sound) for sound in SOURCES)

    @each(test_cases)
    def test_quitting_while_playing_ends_every_thread(self, rig: PlaybackRig, test_case: SoundCase) -> None:
        start_sounding(rig, test_case.sound)

        rig.teardown()

        assert rig.threads.audio_threads() == []
        assert not rig.timeline.open_streams()
        assert _terminated(rig)

    @each(source_cases)
    def test_quitting_while_paused_ends_every_thread(self, rig: PlaybackRig, test_case: SoundCase) -> None:
        start_sounding(rig, test_case.sound)
        rig.pause_or_resume(test_case.sound)

        rig.teardown()

        assert rig.threads.audio_threads() == []
        assert not rig.timeline.open_streams()
        assert _terminated(rig)


class TestQuitPastTheDeadline(BaseTestSuite):
    """Rule 8: a thread that outlives the teardown's deadline is reported, and a writer among them keeps the backend."""

    TestCase = SoundCase
    test_cases = tuple(case(sound) for sound in Sound)

    @each(test_cases)
    def test_quitting_while_a_stream_opens_keeps_the_backend(self, rig: PlaybackRig, test_case: SoundCase) -> None:
        rig.shorten_deadlines()
        rig.expect_errors()
        gate: Gate[OpenCall] = Gate(holds=every_call)
        rig.system.hooks.before_open = gate
        prepare(rig, test_case.sound, Span.SHORT)
        start(rig, test_case.sound)
        gate.wait_for_arrival()

        rig.teardown()
        terminated = _terminated(rig)
        reported = bool(rig.errors.messages)
        gate.open()
        rig.settle()

        assert not terminated
        assert reported

    @each(test_cases)
    def test_quitting_with_a_wedged_writer_keeps_the_backend(self, rig: PlaybackRig, test_case: SoundCase) -> None:
        rig.shorten_deadlines()
        rig.expect_errors()
        gate: Gate[StreamCall] = Gate(holds=from_write(HELD_WRITE))
        rig.system.hooks.before_write = gate
        prepare(rig, test_case.sound, Span.LONG)
        start(rig, test_case.sound)
        gate.wait_for_arrival()

        rig.teardown()
        terminated = _terminated(rig)
        reported = bool(rig.errors.messages)
        gate.open()
        rig.settle()

        assert not terminated
        assert reported

    def test_quitting_while_a_row_renders_reports_the_renderer(self, rig: PlaybackRig) -> None:
        rig.shorten_deadlines()
        rig.expect_errors()
        starved = HeldRow(STARVED_ROW)
        rig.song.before_render = starved
        prepare(rig, Sound.SONG, Span.LONG)
        rig.play(Sound.SONG)
        assert starved.reached.wait(timeout=ROW_SECONDS)

        rig.teardown()
        reported = bool(rig.errors.messages)
        starved.render.set()
        rig.settle()

        assert reported
        assert _terminated(rig)
