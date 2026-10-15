import statistics
import threading
import time
from dataclasses import dataclass, field
from typing import Final, Iterator, List

import numpy as np
import pytest

from sampletones_application.logic.shared.live import Keyboard, LiveKey, LiveKeysLogic, Strike
from sampletones_application.logic.shared.preview_player import PreviewPlayer
from sampletones_core.audio import AudioDeviceManager
from sampletones_core.audio.output import AudioOutput
from sampletones_core.configs import Config
from sampletones_core.constants.audio import DEFAULT_BUFFER_SIZE, DEFAULT_SAMPLE_RATE
from sampletones_shared.types.callback import VoidCallback
from tests.suite.audio.machine import SPEAKERS, FakeAudioSystem
from tests.suite.audio.machine.builders import REAL_TIME, TICKER_BUFFER_SECONDS
from tests.suite.audio.pacing import TickerPacing
from tests.suite.audio.timeline import Timeline, TimelineEvent, Written
from tests.suite.live import held_instrument, instrument_sound, strike

LINGER_SECONDS: Final[float] = 30.0
TEARDOWN_SECONDS: Final[float] = 5.0
WAIT_SECONDS: Final[float] = 5.0
STRIKES: Final[int] = 15
SETTLING_WRITES: Final[int] = 3
LOAD_WORK: Final[int] = 2_000
LOW: Final[int] = 60
HIGH: Final[int] = 67
BLOCK_SECONDS: Final[float] = DEFAULT_BUFFER_SIZE / DEFAULT_SAMPLE_RATE
WARM_BLOCKS: Final[float] = 3.0
COLD_BLOCKS: Final[float] = 4.0


@dataclass
class StampedTimeline(Timeline):
    """A timeline that notes the moment the device first takes a sounding block after each :meth:`expect`."""

    sounded: threading.Event = field(default_factory=threading.Event)
    sounded_at: float = 0.0
    writes: int = 0

    def expect(self) -> None:
        self.sounded.clear()

    def record(self, event: TimelineEvent) -> None:
        super().record(event)
        if not isinstance(event, Written):
            return

        self.writes += 1
        if np.any(event.samples) and not self.sounded.is_set():
            self.sounded_at = time.monotonic()
            self.sounded.set()


class RenderLoad:
    """A thread busy with Python the way the render loop is, contending for the interpreter with the writer."""

    def __init__(self) -> None:
        self._stopped = threading.Event()
        self._thread = threading.Thread(target=self._run, name="RenderLoad", daemon=True)

    @property
    def stop(self) -> VoidCallback:
        return self._stopped.set

    def start(self) -> None:
        self._thread.start()

    def join(self) -> None:
        self._thread.join(timeout=WAIT_SECONDS)

    def _run(self) -> None:
        while not self._stopped.is_set():
            sum(range(LOAD_WORK))


@pytest.fixture
def timeline() -> StampedTimeline:
    return StampedTimeline()


@pytest.fixture
def output(timeline: StampedTimeline) -> Iterator[AudioOutput]:
    """The output over a device playing at its own rate, holding a short buffer ahead as a sound card does."""
    system = FakeAudioSystem(
        (SPEAKERS,),
        default_device=0,
        pacing=TickerPacing(speed=REAL_TIME, buffer_seconds=TICKER_BUFFER_SECONDS),
        timeline=timeline,
    )
    output = AudioOutput(system.driver, post=lambda delivery: None)
    output.configure(AudioDeviceManager(output.catalog).settings)
    yield output
    output.close(deadline_seconds=TEARDOWN_SECONDS)


@pytest.fixture
def keys(output: AudioOutput) -> LiveKeysLogic:
    return LiveKeysLogic(
        PreviewPlayer(output),
        post=lambda delivery: None,
        failed=_unexpected,
        linger_seconds=LINGER_SECONDS,
    )


@pytest.fixture
def load() -> Iterator[RenderLoad]:
    load = RenderLoad()
    load.start()
    yield load
    load.stop()
    load.join()


def _unexpected(error: Exception) -> None:
    raise AssertionError(f"a key failed to sound: {error}")


def _strike(number: int) -> Strike:
    return strike(Keyboard.MIDI, number, instrument_sound(held_instrument(), note=number, config=Config()))


def _strike_to_sound(keys: LiveKeysLogic, timeline: StampedTimeline, number: int) -> float:
    """The seconds from a press until the device takes the first block sounding it."""
    timeline.expect()
    pressed = time.monotonic()
    keys.key_down(_strike(number))
    assert timeline.sounded.wait(timeout=WAIT_SECONDS), "the key never sounded"
    return timeline.sounded_at - pressed


def _wait_for_writes(timeline: StampedTimeline, writes: int) -> None:
    deadline = time.monotonic() + WAIT_SECONDS
    target = timeline.writes + writes
    while timeline.writes < target:
        assert time.monotonic() < deadline, "the device stopped taking writes"
        time.sleep(BLOCK_SECONDS / 4)


class TestStrikeToSound:
    """A key reaches the device within a few blocks of its press while the render loop keeps the interpreter busy.

    The device plays at its own rate and holds ``TICKER_BUFFER_SECONDS`` ahead, and every press is made beside
    a thread running Python flat out, as the render loop does. What a press waits for is the block the writer
    stands in, then its own: a press inside a playback that lingers reaches the next block, and a press with
    nothing playing first starts a writer, opens a stream on a device that opens at once, and builds the
    generators. The figures measure the application's path alone; a real device adds the time it takes to open
    a stream.
    """

    def test_a_press_during_the_linger_sounds_within_a_few_blocks(
        self,
        keys: LiveKeysLogic,
        timeline: StampedTimeline,
        load: RenderLoad,
    ) -> None:
        keys.key_down(_strike(LOW))
        keys.key_up(LiveKey(keyboard=Keyboard.MIDI, number=LOW))
        _wait_for_writes(timeline, SETTLING_WRITES)
        latencies: List[float] = []
        for _ in range(STRIKES):
            latencies.append(_strike_to_sound(keys, timeline, HIGH))
            keys.key_up(LiveKey(keyboard=Keyboard.MIDI, number=HIGH))
            _wait_for_writes(timeline, SETTLING_WRITES)

        load.stop()
        median = statistics.median(latencies)
        print(f"warm strike to sound: median {median * 1000:.1f} ms, worst {max(latencies) * 1000:.1f} ms")
        assert median < WARM_BLOCKS * BLOCK_SECONDS, f"median {median * 1000:.1f} ms"

    def test_a_press_with_nothing_playing_sounds_within_a_few_blocks(
        self,
        keys: LiveKeysLogic,
        output: AudioOutput,
        timeline: StampedTimeline,
        load: RenderLoad,
    ) -> None:
        latencies: List[float] = []
        for _ in range(STRIKES):
            latencies.append(_strike_to_sound(keys, timeline, LOW))
            output.stop_all()
            assert not output.threads.join(deadline_seconds=WAIT_SECONDS)

        load.stop()
        median = statistics.median(latencies)
        print(f"cold strike to sound: median {median * 1000:.1f} ms, worst {max(latencies) * 1000:.1f} ms")
        assert median < COLD_BLOCKS * BLOCK_SECONDS, f"median {median * 1000:.1f} ms"
