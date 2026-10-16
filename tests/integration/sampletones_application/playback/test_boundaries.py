from typing import Final

import numpy as np

from sampletones_application.services.song_player.constants import PREFETCH_SECONDS
from sampletones_core.constants.audio import DEFAULT_BUFFER_SIZE, BufferSize
from sampletones_core.project.song_position import SongPosition
from tests.integration.sampletones_application.playback.material import RATE, REALTIME, SHORT, start_sounding
from tests.integration.sampletones_application.playback.rig import (
    ROW_SECONDS,
    Gate,
    HeldRow,
    PlaybackRig,
    Sound,
    from_write,
)
from tests.suite.audio.machine import StreamCall
from tests.suite.audio.ramp import ramp
from tests.suite.base import BaseTestSuite

SINGLE_SAMPLE_ROWS: Final[int] = 2000
LONG_ROW: Final[int] = 3 * round(PREFETCH_SECONDS * RATE)
STARVED_SONG_ROWS: Final[int] = 8
TAIL_ROW: Final[int] = 100
STARVED_ROW: Final[SongPosition] = SongPosition(order_position=0, row_index=2)
HELD_WRITE: Final[int] = 3
SMALLER_BUFFER: Final[BufferSize] = 256


class TestSongShapes(BaseTestSuite):
    """Rules 3 and 4: a song of any shape plays every sample once, in order, and ends once."""

    def test_an_empty_song_ends_at_once(self, rig: PlaybackRig) -> None:
        rig.compose(())

        rig.play(Sound.SONG)
        rig.settle()

        assert len(rig.timeline.written()) == 0
        assert len(rig.ends(Sound.SONG)) == 1

    def test_one_sample_rows_play_every_sample_once(self, rig: PlaybackRig) -> None:
        rig.compose(((1,) * SINGLE_SAMPLE_ROWS,))

        rig.play(Sound.SONG)
        rig.settle()

        np.testing.assert_array_equal(rig.written(), np.arange(SINGLE_SAMPLE_ROWS))
        rows = [row.position.row_index for row in rig.rows]
        assert rows == sorted(rows)

    def test_a_row_longer_than_the_prefetch_plays_whole(self, rig: PlaybackRig) -> None:
        rig.compose(((LONG_ROW, TAIL_ROW),))

        rig.play(Sound.SONG)
        rig.settle()

        np.testing.assert_array_equal(rig.written(), np.arange(LONG_ROW + TAIL_ROW))


class TestStarvedSong(BaseTestSuite):
    """Rules 4 and 6: a song its synthesizer starves stops at once, and pauses and resumes without a gap."""

    def test_a_starved_song_stops_at_once(self, rig: PlaybackRig) -> None:
        rig.shorten_deadlines()
        rig.expect_errors()
        starved = HeldRow(STARVED_ROW)
        rig.song.before_render = starved
        rig.compose(((DEFAULT_BUFFER_SIZE,) * STARVED_SONG_ROWS,))
        rig.play(Sound.SONG)
        assert starved.reached.wait(timeout=ROW_SECONDS)

        rig.stop_all()
        waits = rig.waits
        starved.render.set()
        rig.settle()

        assert waits == []

    def test_a_starved_song_paused_and_resumed_plays_every_sample_once(self, rig: PlaybackRig) -> None:
        starved = HeldRow(STARVED_ROW)
        rig.song.before_render = starved
        rig.compose(((DEFAULT_BUFFER_SIZE,) * STARVED_SONG_ROWS,))
        rig.play(Sound.SONG)
        assert starved.reached.wait(timeout=ROW_SECONDS)

        rig.pause_or_resume(Sound.SONG)
        starved.render.set()
        rig.pause_or_resume(Sound.SONG)
        rig.settle()

        np.testing.assert_array_equal(rig.written(), np.arange(STARVED_SONG_ROWS * DEFAULT_BUFFER_SIZE))


class TestBufferSize(BaseTestSuite):
    """Rule 5: a buffer size changed while a sound plays leaves its audio whole."""

    def test_a_buffer_size_change_mid_play_keeps_the_audio_whole(self, rig: PlaybackRig) -> None:
        gate: Gate[StreamCall] = Gate(holds=from_write(HELD_WRITE))
        rig.system.hooks.before_write = gate
        rig.load(Sound.RECONSTRUCTION, ramp(SHORT), sample_rate=RATE)
        rig.play(Sound.RECONSTRUCTION)
        gate.wait_for_arrival()

        rig.set_buffer_size(SMALLER_BUFFER)
        gate.open()
        rig.settle()

        np.testing.assert_array_equal(rig.written(), np.arange(SHORT))

    @REALTIME
    def test_a_song_plays_whole_across_a_buffer_size_change(self, rig: PlaybackRig) -> None:
        start_sounding(rig, Sound.SONG)

        rig.set_buffer_size(SMALLER_BUFFER)
        rig.wait_until_written(len(rig.timeline.written()) + DEFAULT_BUFFER_SIZE * HELD_WRITE)
        rig.stop_all()
        rig.settle()

        written = rig.written()
        np.testing.assert_array_equal(written, np.arange(len(written)))
