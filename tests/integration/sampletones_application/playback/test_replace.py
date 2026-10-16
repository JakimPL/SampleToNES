from typing import Final

import numpy as np

from sampletones_core.constants.audio import DEFAULT_BUFFER_SIZE
from tests.integration.sampletones_application.playback.material import (
    HEARD,
    RATE,
    REALTIME,
    SHORT,
    STEPPED,
    grant_and_hold,
    start_sounding,
)
from tests.integration.sampletones_application.playback.rig import Gate, PlaybackRig, Sound, every_call
from tests.suite.audio.machine import OpenCall
from tests.suite.audio.pacing import StepPacing
from tests.suite.audio.ramp import ramp
from tests.suite.base import BaseTestSuite

ORIGINAL: Final[int] = 200_000
GRANTED_WRITES: Final[int] = 4
REPLACEMENT_START: Final[int] = 500_000
SHORTER: Final[int] = 5_000


def _replacement(length: int) -> np.ndarray:
    """Audio whose indices start past the original's, so the device shows which of the two it played."""
    return ramp(length, start=REPLACEMENT_START)


class TestReplaceWhileOpening(BaseTestSuite):
    """Rule 4: audio replaced while the stream opens is what the stream plays, from where the playback stands."""

    def test_audio_replaced_while_the_stream_opens_plays_from_the_start(self, rig: PlaybackRig) -> None:
        gate: Gate[OpenCall] = Gate(holds=every_call)
        rig.system.hooks.before_open = gate
        rig.load(Sound.RECONSTRUCTION, ramp(SHORT), sample_rate=RATE)
        rig.play(Sound.RECONSTRUCTION)
        gate.wait_for_arrival()

        rig.load(Sound.RECONSTRUCTION, _replacement(SHORT), sample_rate=RATE)
        gate.open()
        rig.settle()

        np.testing.assert_array_equal(rig.written(), np.arange(REPLACEMENT_START, REPLACEMENT_START + SHORT))


@STEPPED
class TestReplaceWhilePaused(BaseTestSuite):
    """Rule 4: audio replaced under a paused playback plays on from where the playback stood."""

    def test_audio_replaced_while_paused_resumes_where_it_stood(self, rig: PlaybackRig, steps: StepPacing) -> None:
        rig.load(Sound.RECONSTRUCTION, ramp(ORIGINAL), sample_rate=RATE)
        rig.play(Sound.RECONSTRUCTION)
        grant_and_hold(rig, steps, GRANTED_WRITES)
        rig.pause_or_resume(Sound.RECONSTRUCTION)
        steps.grant(1)
        stood = (GRANTED_WRITES + 1) * DEFAULT_BUFFER_SIZE
        rig.wait_for_device(lambda: len(rig.timeline.written()) == stood, what="the write in flight")

        rig.load(Sound.RECONSTRUCTION, _replacement(ORIGINAL), sample_rate=RATE)
        rig.pause_or_resume(Sound.RECONSTRUCTION)
        steps.grant(GRANTED_WRITES)
        rig.wait_until_written(stood + GRANTED_WRITES * DEFAULT_BUFFER_SIZE)
        steps.grant(ORIGINAL)
        rig.stop_all()

        written = rig.written()
        np.testing.assert_array_equal(written[:stood], np.arange(stood))
        np.testing.assert_array_equal(
            written[stood:],
            np.arange(REPLACEMENT_START + stood, REPLACEMENT_START + len(written)),
        )


@REALTIME
class TestReplaceAfterTheEnd(BaseTestSuite):
    """Rules 3 and 4: audio replaced under a playback that lost the output or passed its end stays silent."""

    def test_audio_replaced_after_a_takeover_stays_silent(self, rig: PlaybackRig) -> None:
        start_sounding(rig, Sound.RECONSTRUCTION)
        start_sounding(rig, Sound.SONG)

        rig.load(Sound.RECONSTRUCTION, _replacement(ORIGINAL), sample_rate=RATE)
        rig.wait_until_written(len(rig.timeline.written()) + HEARD)
        rig.stop_all()
        rig.settle()

        assert not np.any(rig.written() >= REPLACEMENT_START)
        assert not rig.engaged(Sound.RECONSTRUCTION)

    def test_shorter_audio_than_the_position_ends_the_sound(self, rig: PlaybackRig) -> None:
        rig.load(Sound.RECONSTRUCTION, ramp(ORIGINAL), sample_rate=RATE)
        rig.play(Sound.RECONSTRUCTION)
        rig.wait_until_written(SHORTER + HEARD)

        rig.load(Sound.RECONSTRUCTION, _replacement(SHORTER), sample_rate=RATE)
        rig.settle()

        assert not np.any(rig.written() >= REPLACEMENT_START)
        assert not rig.engaged(Sound.RECONSTRUCTION)
