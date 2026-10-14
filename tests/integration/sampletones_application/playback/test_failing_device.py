from pathlib import Path
from typing import Final

import numpy as np

from tests.integration.sampletones_application.playback.breaks import SECOND_STREAM, UNREAD_FILE, broken
from tests.integration.sampletones_application.playback.material import (
    REALTIME,
    SHORT,
    SoundCase,
    Span,
    case,
    each,
    played_through,
    prepare,
    start,
)
from tests.integration.sampletones_application.playback.rig import (
    PREVIEWS,
    SOURCES,
    Fault,
    Gate,
    PlaybackRig,
    Sound,
    every_call,
    from_write,
)
from tests.suite.audio.machine import OpenCall, StreamCall
from tests.suite.base import BaseTestSuite

HELD_WRITE: Final[int] = 2
FAILING_WRITE: Final[int] = 2
DEVICE_FAILURE: Final[str] = "The device failed"
HANDLER_FAILURE: Final[str] = "The mark could not be drawn"
UNREADABLE_NAME: Final[str] = "unreadable.wav"
UNREADABLE_BYTES: Final[bytes] = b"neither a header nor samples"


class TestSlowOpen(BaseTestSuite):
    """Rule 1: a sound holds the output from its claim, while its stream still opens."""

    TestCase = SoundCase
    source_cases = tuple(case(sound) for sound in SOURCES)
    preview_cases = tuple(case(sound) for sound in PREVIEWS)

    @each(source_cases)
    def test_a_source_is_engaged_while_its_stream_opens(self, rig: PlaybackRig, test_case: SoundCase) -> None:
        gate: Gate[OpenCall] = Gate(holds=every_call)
        rig.system.hooks.before_open = gate
        prepare(rig, test_case.sound, Span.SHORT)
        start(rig, test_case.sound)
        gate.wait_for_arrival()

        engaged = rig.engaged(test_case.sound)
        stop_available = rig.stop_available
        gate.open()
        rig.settle()

        assert engaged
        assert stop_available

    @each(preview_cases)
    def test_stop_is_offered_while_a_preview_opens(self, rig: PlaybackRig, test_case: SoundCase) -> None:
        gate: Gate[OpenCall] = Gate(holds=every_call)
        rig.system.hooks.before_open = gate
        prepare(rig, test_case.sound, Span.SHORT)
        start(rig, test_case.sound)
        gate.wait_for_arrival()

        stop_available = rig.stop_available
        gate.open()
        rig.settle()

        assert stop_available


@REALTIME
class TestWedgedWrite(BaseTestSuite):
    """Rule 2: a sound taking the output from a writer wedged in a write opens its stream once the wedged one closed."""

    TestCase = SoundCase
    test_cases = tuple(case(sound, broken(SECOND_STREAM)) for sound in (Sound.INSTRUCTION, Sound.SONG, Sound.FILE))

    @each(test_cases)
    def test_a_takeover_from_a_wedged_writer_keeps_one_stream_open(
        self,
        rig: PlaybackRig,
        test_case: SoundCase,
    ) -> None:
        rig.shorten_deadlines()
        rig.expect_errors()
        gate: Gate[StreamCall] = Gate(holds=from_write(HELD_WRITE))
        rig.system.hooks.before_write = gate
        prepare(rig, Sound.RECONSTRUCTION, Span.LONG)
        rig.play(Sound.RECONSTRUCTION)
        gate.wait_for_arrival()

        prepare(rig, test_case.sound, Span.LONG)
        rig.play(test_case.sound)
        rig.wait_for(lambda: len(rig.timeline.streams()) == 2 or bool(rig.told), what="the second sound")
        rig.system.hooks.before_write = None
        gate.open()
        rig.stop_all()
        rig.settle()

        assert rig.timeline.most_streams_open() == 1
        assert rig.told == []


class TestFailingCalls(BaseTestSuite):
    """Rule 7: a device failing a call has the failure told once, and the sound ends."""

    TestCase = SoundCase
    test_cases = tuple(case(sound) for sound in Sound)

    @each(test_cases)
    def test_a_refused_open_is_told_once(self, rig: PlaybackRig, test_case: SoundCase) -> None:
        rig.expect_errors()
        rig.system.hooks.before_open = Fault(fails=every_call, message=DEVICE_FAILURE)

        played_through(rig, test_case.sound)

        _assert_told_once_and_ended(rig, test_case.sound)

    @each(test_cases)
    def test_a_failed_write_is_told_once(self, rig: PlaybackRig, test_case: SoundCase) -> None:
        rig.expect_errors()
        rig.system.hooks.before_write = Fault(fails=from_write(FAILING_WRITE), message=DEVICE_FAILURE)

        played_through(rig, test_case.sound)

        _assert_told_once_and_ended(rig, test_case.sound)

    @each(test_cases)
    def test_a_failed_drain_is_told_once(self, rig: PlaybackRig, test_case: SoundCase) -> None:
        rig.expect_errors()
        rig.system.hooks.before_drain = Fault(fails=every_call, message=DEVICE_FAILURE)

        played_through(rig, test_case.sound)

        _assert_told_once_and_ended(rig, test_case.sound)

    @each(test_cases)
    def test_a_failed_close_is_told_once(self, rig: PlaybackRig, test_case: SoundCase) -> None:
        rig.expect_errors()
        rig.system.hooks.before_close = Fault(fails=every_call, message=DEVICE_FAILURE)

        played_through(rig, test_case.sound)

        _assert_told_once_and_ended(rig, test_case.sound)


def _assert_told_once_and_ended(rig: PlaybackRig, sound: Sound) -> None:
    assert len(rig.told) == 1
    if sound in SOURCES:
        assert not rig.engaged(sound)


class TestUnreadableFile(BaseTestSuite):
    """Rule 7: a file preview that cannot read its file has the failure told once, and sounds nothing."""

    @broken(UNREAD_FILE)
    def test_an_unreadable_file_is_told_once(self, rig: PlaybackRig, tmp_path: Path) -> None:
        unreadable = tmp_path / UNREADABLE_NAME
        unreadable.write_bytes(UNREADABLE_BYTES)
        rig.stack.file = unreadable

        rig.autoplay(Sound.FILE)
        rig.settle()

        assert len(rig.told) == 1
        assert not rig.timeline.streams()


class TestBusyDevice(BaseTestSuite):
    """Rule 7: a device another program holds refuses the sound once, and plays the next one asked for once free."""

    def test_a_busy_device_refuses_once_and_recovers(self, rig: PlaybackRig) -> None:
        played_through(rig, Sound.RECONSTRUCTION)

        rig.system.occupy()
        rig.play(Sound.RECONSTRUCTION)
        rig.settle()
        told = len(rig.told)
        rig.system.free()
        rig.play(Sound.RECONSTRUCTION)
        rig.settle()

        assert told == 1
        assert len(rig.told) == 1
        np.testing.assert_array_equal(rig.written(), np.concatenate([np.arange(SHORT), np.arange(SHORT)]))


class TestRaisingHandler(BaseTestSuite):
    """Rule 3: an owner whose handler raises on a report leaves the sound playing through to its end."""

    def test_a_raising_mark_handler_leaves_the_playback_whole(self, rig: PlaybackRig) -> None:
        rig.expect_errors()
        handler = RaisingHandler()
        rig.stack.reconstruction.on_position_changed = handler

        played_through(rig, Sound.RECONSTRUCTION)
        handler.raising = False

        assert handler.raised
        np.testing.assert_array_equal(rig.written(), np.arange(SHORT))
        assert not rig.engaged(Sound.RECONSTRUCTION)


class RaisingHandler:
    """A mark handler that fails on every report until the case lets it rest."""

    def __init__(self) -> None:
        self.raising: bool = True
        self.raised: int = 0

    def __call__(self, _position: int) -> None:
        if self.raising:
            self.raised += 1
            raise RuntimeError(HANDLER_FAILURE)
