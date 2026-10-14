from typing import Final

import numpy as np
import pytest

from sampletones_core.constants.audio import SampleRate
from tests.integration.sampletones_application.playback.material import (
    HEADPHONES_INDEX,
    HEADPHONES_RATE,
    RATE,
    SHORT,
    SoundCase,
    Span,
    case,
    each,
    prepare,
    start,
)
from tests.integration.sampletones_application.playback.rig import BUFFERS, PlaybackRig, Sound
from tests.suite.audio.ramp import ramp
from tests.suite.base import BaseTestSuite

LENGTH_TOLERANCE: Final[float] = 0.01
FILE_RATE: Final[SampleRate] = 96000
STEREO: Final[int] = 2


def _played(rig: PlaybackRig, sound: Sound) -> int:
    """Plays a short sound to its end, and answers how many samples the device received for it."""
    before = len(rig.timeline.written())
    prepare(rig, sound, Span.SHORT)
    start(rig, sound)
    rig.settle()
    return len(rig.timeline.written()) - before


def _assert_lasts(received: int, expected: float) -> None:
    assert received == pytest.approx(expected, rel=LENGTH_TOLERANCE)


class TestRates(BaseTestSuite):
    """Rule 5: a sound plays at its own pitch and length on a device of any rate."""

    TestCase = SoundCase
    test_cases = tuple(case(sound) for sound in (*BUFFERS, Sound.FILE))
    rendered_cases = tuple(case(sound) for sound in (Sound.AUDITION, Sound.VOICE))

    @each(test_cases)
    def test_a_sound_at_the_device_rate_plays_every_sample_once(self, rig: PlaybackRig, test_case: SoundCase) -> None:
        _played(rig, test_case.sound)

        np.testing.assert_array_equal(rig.written(), np.arange(SHORT))

    @each(test_cases)
    def test_a_sound_keeps_its_length_on_a_faster_device(self, rig: PlaybackRig, test_case: SoundCase) -> None:
        rig.change_device(HEADPHONES_INDEX, sample_rate=HEADPHONES_RATE)

        _assert_lasts(_played(rig, test_case.sound), SHORT * HEADPHONES_RATE / RATE)

    @each(rendered_cases)
    def test_a_rendered_sound_keeps_its_length_on_a_faster_device(
        self,
        rig: PlaybackRig,
        test_case: SoundCase,
    ) -> None:
        at_its_rate = _played(rig, test_case.sound)
        rig.change_device(HEADPHONES_INDEX, sample_rate=HEADPHONES_RATE)

        _assert_lasts(_played(rig, test_case.sound), at_its_rate * HEADPHONES_RATE / RATE)

    def test_a_96_khz_stereo_file_keeps_its_length(self, rig: PlaybackRig) -> None:
        frames = SHORT
        rig.load(Sound.FILE, np.repeat(ramp(frames)[:, np.newaxis], STEREO, axis=1), sample_rate=FILE_RATE)
        rig.autoplay(Sound.FILE)
        rig.settle()

        _assert_lasts(len(rig.timeline.written()), frames * RATE / FILE_RATE)
