from dataclasses import dataclass
from enum import Enum
from typing import Final, Sequence, Tuple

import pytest
from pytest import MarkDecorator

from sampletones_core.constants.audio import DEFAULT_SAMPLE_RATE, SampleRate
from tests.integration.sampletones_application.playback.rig import BUFFERS, PlaybackRig, Sound
from tests.suite.audio.pacing import StepPacing
from tests.suite.audio.ramp import ramp
from tests.suite.case import BaseRegularTestCase

RATE: Final[SampleRate] = DEFAULT_SAMPLE_RATE
HEADPHONES_INDEX: Final[int] = 1
HEADPHONES_RATE: Final[SampleRate] = 48000
SHORT: Final[int] = RATE // 4
LONG: Final[int] = RATE * 20
ROW: Final[int] = 1024
SHORT_SONG: Final[Tuple[Tuple[int, ...], ...]] = ((ROW,) * 4,) * 2
LONG_SONG: Final[Tuple[Tuple[int, ...], ...]] = ((ROW,) * 16,) * 50
HEARD: Final[int] = 4096
WRITER_SECONDS: Final[float] = 10.0
REALTIME: Final[MarkDecorator] = pytest.mark.realtime
STEPPED: Final[MarkDecorator] = pytest.mark.stepped
REALTIME_MARKER: Final[str] = REALTIME.name
STEPPED_MARKER: Final[str] = STEPPED.name


class Span(Enum):
    """How long a prepared sound lasts: over in a moment on a fast device, or sounding on a real-time one."""

    SHORT = "short"
    LONG = "long"


@dataclass(frozen=True, kw_only=True)
class PlaybackCase(BaseRegularTestCase):
    """A case a rule is held to."""


@dataclass(frozen=True, kw_only=True)
class SoundCase(PlaybackCase):
    """One sound a rule is held to."""

    sound: Sound


@dataclass(frozen=True, kw_only=True)
class TakeoverCase(PlaybackCase):
    """A source sounding, and the source a reader starts over it."""

    taken: Sound
    taker: Sound


def case(sound: Sound) -> SoundCase:
    return SoundCase(sound=sound, label=sound.value)


def takeover(taken: Sound, taker: Sound) -> TakeoverCase:
    return TakeoverCase(taken=taken, taker=taker, label=f"{taker.value}_over_{taken.value}")


def each(test_cases: Sequence[PlaybackCase]) -> MarkDecorator:
    """Runs a case once per entry."""
    return pytest.mark.parametrize(
        "test_case",
        [pytest.param(test_case, id=test_case.label) for test_case in test_cases],
    )


def prepare(rig: PlaybackRig, sound: Sound, span: Span) -> None:
    """Gives a sound its material: a ramp for a player or a file, rows of the ramp for the song.

    An audition and a voice preview sound what the instrument renders, so they take no material.
    """
    length = SHORT if span is Span.SHORT else LONG
    match sound:
        case Sound.RECONSTRUCTION | Sound.INSTRUCTION | Sound.FILE:
            rig.load(sound, ramp(length), sample_rate=RATE)
        case Sound.SONG:
            rig.compose(SHORT_SONG if span is Span.SHORT else LONG_SONG)
        case Sound.AUDITION | Sound.VOICE:
            return


def start(rig: PlaybackRig, sound: Sound) -> None:
    """Starts a sound the way a reader most often does: a source from its start, a preview by picking it."""
    match sound:
        case Sound.RECONSTRUCTION | Sound.INSTRUCTION | Sound.SONG | Sound.AUDITION:
            rig.play(sound)
        case Sound.VOICE | Sound.FILE:
            rig.autoplay(sound)


def start_sounding(rig: PlaybackRig, sound: Sound) -> None:
    """Starts a long sound and waits until the device has played some of it."""
    written = len(rig.timeline.written())
    prepare(rig, sound, Span.LONG)
    start(rig, sound)
    rig.wait_until_written(written + HEARD)


def played_through(rig: PlaybackRig, sound: Sound) -> None:
    """Plays a short sound to its end and lets every report land."""
    prepare(rig, sound, Span.SHORT)
    start(rig, sound)
    rig.settle()


def grant_and_hold(rig: PlaybackRig, steps: StepPacing, writes: int) -> None:
    """Lets ``writes`` more writes through a stepped device, and waits until the writer stands inside the next one."""
    admitted = steps.admitted
    steps.grant(writes)
    rig.wait_for_device(lambda: steps.admitted == admitted + writes, what="the granted writes")
    assert steps.wait_for_writer(timeout=WRITER_SECONDS)


def ramp_material(sound: Sound) -> bool:
    """Whether what the sound plays is the ramp, which reads back as the document indices it played."""
    return sound in BUFFERS or sound in (Sound.FILE, Sound.SONG)
