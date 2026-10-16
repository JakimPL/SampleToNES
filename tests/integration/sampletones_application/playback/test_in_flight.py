from typing import Final

import numpy as np

from sampletones_core.constants.audio import DEFAULT_BUFFER_SIZE
from tests.integration.sampletones_application.playback.material import (
    SHORT,
    SoundCase,
    Span,
    case,
    each,
    prepare,
    start,
)
from tests.integration.sampletones_application.playback.rig import Gate, PlaybackRig, Sound, every_call
from tests.suite.audio.machine import OpenCall, StreamCall
from tests.suite.base import BaseTestSuite

CLICKED: Final[int] = SHORT // 2
LAST_WRITE: Final[int] = SHORT // DEFAULT_BUFFER_SIZE


class TestStopRacingTheEnd(BaseTestSuite):
    """Rule 3: a stop arriving while the last block is written ends the sound once."""

    TestCase = SoundCase
    test_cases = (
        case(Sound.RECONSTRUCTION),
        case(Sound.SONG),
        case(Sound.FILE),
    )

    @each(test_cases)
    def test_a_stop_racing_the_natural_end_ends_the_sound_once(self, rig: PlaybackRig, test_case: SoundCase) -> None:
        rig.shorten_deadlines()
        rig.expect_errors()
        gate: Gate[StreamCall] = Gate(holds=lambda call: call.writes == _last_write(rig, test_case.sound))
        rig.system.hooks.before_write = gate
        prepare(rig, test_case.sound, Span.SHORT)
        start(rig, test_case.sound)
        gate.wait_for_arrival()

        rig.stop_all()
        gate.open()
        rig.settle()

        assert len(rig.ends(test_case.sound)) == 1


def _last_write(rig: PlaybackRig, sound: Sound) -> int:
    """The index of the last block a short sound writes, counted from zero."""
    if sound is Sound.SONG:
        return rig.song.length // DEFAULT_BUFFER_SIZE - 1

    return LAST_WRITE


class TestClickAroundTheEnd(BaseTestSuite):
    """Rule 4: a click on the waveform as the sound ends plays from the click, whichever side of the end it lands."""

    def test_a_click_between_the_end_and_its_report_plays_from_the_click(self, rig: PlaybackRig) -> None:
        prepare(rig, Sound.RECONSTRUCTION, Span.SHORT)
        start(rig, Sound.RECONSTRUCTION)
        rig.wait_for_device(
            lambda: not rig.timeline.open_streams() and not rig.threads.audio_threads(),
            what="the end of the sound",
        )
        heard = len(rig.marks(Sound.RECONSTRUCTION))

        rig.seek(Sound.RECONSTRUCTION, CLICKED)
        rig.settle()

        written = rig.written()
        np.testing.assert_array_equal(written, np.concatenate([np.arange(SHORT), np.arange(CLICKED, SHORT)]))
        after = rig.positions(Sound.RECONSTRUCTION)[heard:]
        assert after[0] >= CLICKED

    def test_a_click_while_the_sound_winds_down_plays_from_the_click(self, rig: PlaybackRig) -> None:
        gate: Gate[StreamCall] = Gate(holds=every_call)
        rig.system.hooks.before_drain = gate
        prepare(rig, Sound.RECONSTRUCTION, Span.SHORT)
        start(rig, Sound.RECONSTRUCTION)
        gate.wait_for_arrival()

        rig.seek(Sound.RECONSTRUCTION, CLICKED)
        gate.open()
        rig.settle()

        written = rig.written()
        np.testing.assert_array_equal(written[SHORT:], np.arange(CLICKED, SHORT))


class TestStopWhileOpening(BaseTestSuite):
    """Rule 6: Stop pressed while a stream still opens leaves the device silent once it opens."""

    TestCase = SoundCase
    test_cases = tuple(case(sound) for sound in Sound)

    @each(test_cases)
    def test_stop_while_the_stream_opens_sounds_nothing(self, rig: PlaybackRig, test_case: SoundCase) -> None:
        rig.shorten_deadlines()
        rig.expect_errors()
        gate: Gate[OpenCall] = Gate(holds=every_call)
        rig.system.hooks.before_open = gate
        prepare(rig, test_case.sound, Span.SHORT)
        start(rig, test_case.sound)
        gate.wait_for_arrival()

        rig.stop_all()
        gate.open()
        rig.settle()

        assert len(rig.timeline.written()) == 0
