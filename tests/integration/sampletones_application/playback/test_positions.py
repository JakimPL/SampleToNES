from typing import Final, List

import numpy as np

from sampletones_application.logic.shared.live import Keyboard
from sampletones_core.constants.audio import DEFAULT_BUFFER_SIZE, START_OF_AUDIO
from tests.integration.sampletones_application.playback.material import (
    LONG,
    REALTIME,
    SHORT_SONG,
    STEPPED,
    SoundCase,
    Span,
    case,
    each,
    grant_and_hold,
    played_through,
    prepare,
    start_sounding,
)
from tests.integration.sampletones_application.playback.rig import BUFFERS, PLAYED_KEY, PlaybackRig, Sound
from tests.suite.audio.pacing import StepPacing
from tests.suite.base import BaseTestSuite

GRANTED_WRITES: Final[int] = 4
SEEK_TARGET: Final[int] = 300_000
SONG_SEEK_ORDER: Final[int] = 30


def _held_then_lifted(rig: PlaybackRig) -> None:
    """Holds a key until the device has played some of its note, then lifts it and lets every report land."""
    start_sounding(rig, Sound.KEYS)
    rig.lift(PLAYED_KEY, keyboard=Keyboard.MIDI)
    rig.settle()


def _drawn(rig: PlaybackRig, sound: Sound) -> List[int]:
    """The positions an owner drew, leaving out the start of the audio, where a mark comes off at an end."""
    return [position for position in rig.positions(sound) if position != START_OF_AUDIO]


class TestOrder(BaseTestSuite):
    """Rule 4: a sound's positions arrive in order, and before its end report."""

    TestCase = SoundCase
    test_cases = tuple(case(sound) for sound in BUFFERS)

    @each(test_cases)
    def test_positions_arrive_in_order(self, rig: PlaybackRig, test_case: SoundCase) -> None:
        played_through(rig, test_case.sound)

        drawn = _drawn(rig, test_case.sound)
        assert drawn
        assert drawn == sorted(drawn)

    @each(test_cases)
    def test_every_position_lands_before_the_end_report(self, rig: PlaybackRig, test_case: SoundCase) -> None:
        played_through(rig, test_case.sound)

        assert all(mark.ends_heard == 0 for mark in rig.marks(test_case.sound) if mark.position != START_OF_AUDIO)

    def test_a_held_keys_positions_arrive_in_order(self, rig: PlaybackRig) -> None:
        _held_then_lifted(rig)

        drawn = _drawn(rig, Sound.KEYS)
        assert drawn
        assert drawn == sorted(drawn)

    def test_every_position_of_a_key_lands_before_its_end_report(self, rig: PlaybackRig) -> None:
        _held_then_lifted(rig)

        assert _drawn(rig, Sound.KEYS)
        assert all(mark.ends_heard == 0 for mark in rig.marks(Sound.KEYS) if mark.position != START_OF_AUDIO)

    def test_the_song_rows_arrive_in_order(self, rig: PlaybackRig) -> None:
        played_through(rig, Sound.SONG)

        rows = [(row.position.order_position, row.position.row_index) for row in rig.rows]
        assert rows == sorted(rows)
        assert len(rows) == sum(len(order) for order in SHORT_SONG)


@STEPPED
class TestWritten(BaseTestSuite):
    """Rule 4: a position names audio the device has received, and the device holds a write until it is granted."""

    TestCase = SoundCase
    test_cases = (
        case(Sound.RECONSTRUCTION),
        case(Sound.INSTRUCTION),
        case(Sound.KEYS),
    )

    @each(test_cases)
    def test_a_position_names_audio_the_device_received(
        self,
        rig: PlaybackRig,
        steps: StepPacing,
        test_case: SoundCase,
    ) -> None:
        prepare(rig, test_case.sound, Span.LONG)
        rig.play(test_case.sound)
        grant_and_hold(rig, steps, GRANTED_WRITES)
        rig.drain()

        drawn = [mark for mark in rig.marks(test_case.sound) if mark.position != START_OF_AUDIO]
        steps.grant(LONG)
        assert drawn
        assert all(mark.position <= mark.written for mark in drawn)

    def test_a_song_row_names_audio_the_device_received(self, rig: PlaybackRig, steps: StepPacing) -> None:
        rig.compose(((DEFAULT_BUFFER_SIZE,) * 16,) * 4)
        rig.play(Sound.SONG)
        grant_and_hold(rig, steps, GRANTED_WRITES)
        rig.drain()

        rows = rig.rows
        steps.grant(LONG)
        assert rows
        assert all(rig.song.start_of(row.position) + DEFAULT_BUFFER_SIZE <= row.written for row in rows)


@REALTIME
class TestSeek(BaseTestSuite):
    """Rule 4: a position read after a seek reads the seek, and the device plays on from it."""

    TestCase = SoundCase
    test_cases = tuple(case(sound) for sound in BUFFERS)

    @each(test_cases)
    def test_a_mark_after_a_seek_reads_the_seek(self, rig: PlaybackRig, test_case: SoundCase) -> None:
        start_sounding(rig, test_case.sound)
        heard = len(rig.marks(test_case.sound))

        rig.seek(test_case.sound, SEEK_TARGET)
        rig.wait_until_written(len(rig.timeline.written()) + DEFAULT_BUFFER_SIZE * GRANTED_WRITES)

        after = [mark.position for mark in rig.marks(test_case.sound)[heard:]]
        assert after
        assert all(position >= SEEK_TARGET for position in after)

    @each(test_cases)
    def test_the_device_plays_on_from_the_seek(self, rig: PlaybackRig, test_case: SoundCase) -> None:
        start_sounding(rig, test_case.sound)

        rig.seek(test_case.sound, SEEK_TARGET)
        rig.wait_until_written(len(rig.timeline.written()) + DEFAULT_BUFFER_SIZE * GRANTED_WRITES)
        rig.stop_all()

        written = rig.written()
        jump = int(np.flatnonzero(written == SEEK_TARGET)[0])
        np.testing.assert_array_equal(written[jump:], np.arange(SEEK_TARGET, SEEK_TARGET + len(written) - jump))

    def test_song_rows_after_a_seek_read_the_seek(self, rig: PlaybackRig) -> None:
        start_sounding(rig, Sound.SONG)

        rig.seek_order(SONG_SEEK_ORDER)
        heard = len(rig.rows)
        rig.wait_for(
            lambda: any(row.position.order_position == SONG_SEEK_ORDER for row in rig.rows[heard:]),
            what="a row of the order sought",
        )

        after = [row.position.order_position for row in rig.rows[heard:]]
        assert all(order >= SONG_SEEK_ORDER for order in after)
