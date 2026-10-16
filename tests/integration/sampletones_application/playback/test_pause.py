from typing import Final

import numpy as np

from sampletones_core.constants.audio import DEFAULT_BUFFER_SIZE
from sampletones_core.project.song_position import SongPosition
from tests.integration.sampletones_application.playback.material import (
    HEADPHONES_INDEX,
    HEADPHONES_RATE,
    HEARD,
    LONG,
    RATE,
    REALTIME,
    STEPPED,
    SoundCase,
    TakeoverCase,
    case,
    each,
    grant_and_hold,
    start_sounding,
    takeover,
)
from tests.integration.sampletones_application.playback.rig import ROW_SECONDS, FailingRow, PlaybackRig, Sound
from tests.suite.audio.pacing import StepPacing
from tests.suite.audio.ramp import ramp
from tests.suite.audio.timeline import Opened, Written
from tests.suite.base import BaseTestSuite

GRANTED_WRITES: Final[int] = 4
SEEK_TARGET: Final[int] = 300_000
FAILING_ORDER: Final[int] = 1
FAILING_ROW: Final[int] = 4


def _written_after_the_taker_opened(rig: PlaybackRig, taken_stream: int) -> int:
    """How many blocks reached the taken stream once the stream after it opened."""
    events = rig.timeline.events()
    opened = next(
        index for index, event in enumerate(events) if isinstance(event, Opened) and event.stream > taken_stream
    )
    return sum(1 for event in events[opened:] if isinstance(event, Written) and event.stream == taken_stream)


@REALTIME
class TestPausedAndTaken(BaseTestSuite):
    """Rules 1 and 3: a paused source another takes the output from hears its end, and stays silent."""

    TestCase = TakeoverCase
    test_cases = (
        takeover(Sound.RECONSTRUCTION, Sound.SONG),
        takeover(Sound.SONG, Sound.RECONSTRUCTION),
    )

    @each(test_cases)
    def test_a_paused_source_taken_over_stays_silent(self, rig: PlaybackRig, test_case: TakeoverCase) -> None:
        start_sounding(rig, test_case.taken)
        rig.pause_or_resume(test_case.taken)
        taken_stream = rig.timeline.streams()[-1]

        start_sounding(rig, test_case.taker)
        rig.stop_all()
        rig.settle()

        assert not rig.engaged(test_case.taken)
        assert _written_after_the_taker_opened(rig, taken_stream) == 0

    @each(test_cases)
    def test_a_paused_source_taken_over_hears_its_end_once(
        self,
        rig: PlaybackRig,
        test_case: TakeoverCase,
    ) -> None:
        start_sounding(rig, test_case.taken)
        rig.pause_or_resume(test_case.taken)

        start_sounding(rig, test_case.taker)

        ends = rig.ends(test_case.taken)
        assert len(ends) == 1
        assert not ends[0].holding


@REALTIME
class TestPausedAcrossADeviceChange(BaseTestSuite):
    """Rule 2: a source paused before a device change sounds on the new device once resumed."""

    TestCase = SoundCase
    test_cases = tuple(case(sound) for sound in (Sound.RECONSTRUCTION, Sound.SONG))

    @each(test_cases)
    def test_a_resumed_source_sounds_on_the_new_device(self, rig: PlaybackRig, test_case: SoundCase) -> None:
        start_sounding(rig, test_case.sound)
        rig.pause_or_resume(test_case.sound)

        rig.change_device(HEADPHONES_INDEX, sample_rate=HEADPHONES_RATE)
        rig.pause_or_resume(test_case.sound)
        rig.wait_for(lambda: rig.timeline.of(Opened)[-1].device == HEADPHONES_INDEX, what="a stream on the headphones")
        rig.wait_until_written(len(rig.timeline.written()) + HEARD)
        rig.stop_all()
        rig.settle()

        assert rig.told == []
        assert rig.timeline.most_streams_open() == 1


@STEPPED
class TestSeekWhilePaused(BaseTestSuite):
    """Rule 4: a playback sought while paused resumes from the seek."""

    def test_a_seek_while_paused_resumes_from_the_seek(self, rig: PlaybackRig, steps: StepPacing) -> None:
        rig.load(Sound.RECONSTRUCTION, ramp(LONG), sample_rate=RATE)
        rig.play(Sound.RECONSTRUCTION)
        grant_and_hold(rig, steps, GRANTED_WRITES)
        rig.pause_or_resume(Sound.RECONSTRUCTION)
        steps.grant(1)
        stood = (GRANTED_WRITES + 1) * DEFAULT_BUFFER_SIZE
        rig.wait_for_device(lambda: len(rig.timeline.written()) == stood, what="the write in flight")

        rig.seek(Sound.RECONSTRUCTION, SEEK_TARGET)
        rig.pause_or_resume(Sound.RECONSTRUCTION)
        steps.grant(GRANTED_WRITES)
        rig.wait_until_written(stood + GRANTED_WRITES * DEFAULT_BUFFER_SIZE)
        steps.grant(LONG)
        rig.stop_all()

        written = rig.written()
        np.testing.assert_array_equal(written[stood:], np.arange(SEEK_TARGET, SEEK_TARGET + len(written) - stood))


@REALTIME
class TestFailingWhilePaused(BaseTestSuite):
    """Rule 7: a song whose synthesizer fails while it stands paused has the failure told once."""

    def test_a_failure_while_paused_is_told_once(self, rig: PlaybackRig) -> None:
        rig.expect_errors()
        failing = FailingRow(SongPosition(order_position=FAILING_ORDER, row_index=FAILING_ROW))
        rig.song.before_render = failing
        start_sounding(rig, Sound.SONG)
        assert failing.reached.wait(timeout=ROW_SECONDS)

        rig.pause_or_resume(Sound.SONG)
        failing.fail.set()
        rig.wait_for(lambda: bool(rig.errors.messages), what="the synthesis failure")
        rig.stop_all()
        rig.settle()

        assert len(rig.told) == 1
