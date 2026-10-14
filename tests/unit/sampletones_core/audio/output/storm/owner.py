import random
import time
from dataclasses import dataclass
from enum import Enum
from functools import partial
from typing import Callable, Dict, Final, List, Optional, Tuple

from sampletones_core.audio.output import AudioOutput, OutputSettings, Playback
from sampletones_core.constants.audio import DEFAULT_BUFFER_SIZE, BufferSize
from sampletones_shared.exceptions import NoOutputDeviceError
from tests.suite.audio.machine import HEADPHONES, SPEAKERS, FakeAudioSystem

from .listener import StormListener
from .record import Sounding, StormRecord
from .source import StormMark, StormSound, StormSource


class Operation(Enum):
    PLAY = "play"
    STOP = "stop"
    PAUSE = "pause"
    RESUME = "resume"
    SEEK = "seek"
    FAIL_ASIDE = "fail aside"
    STOP_ALL = "stop all"
    CONFIGURE = "configure"
    REFRESH = "refresh"
    UNPLUG = "unplug the headphones"
    PLUG = "plug the headphones in"


WEIGHTS: Final[Dict[Operation, int]] = {
    Operation.PLAY: 30,
    Operation.STOP: 12,
    Operation.PAUSE: 8,
    Operation.RESUME: 8,
    Operation.SEEK: 10,
    Operation.FAIL_ASIDE: 4,
    Operation.STOP_ALL: 3,
    Operation.CONFIGURE: 5,
    Operation.REFRESH: 3,
    Operation.UNPLUG: 1,
    Operation.PLUG: 1,
}
RANKS: Final[Tuple[int, ...]] = (0, 1, 2)
BUFFER_SIZES_TRIED: Final[Tuple[BufferSize, ...]] = (256, 512, 1024)
RECENT: Final[int] = 4
SEEK_RANGE: Final[int] = 100_000
ENDLESS_CHANCE: Final[float] = 0.25
SHORT_CHANCE: Final[float] = 0.35
SHORT_FRAMES: Final[Tuple[int, int]] = (1, 3 * DEFAULT_BUFFER_SIZE)
LONG_FRAMES: Final[Tuple[int, int]] = (4 * DEFAULT_BUFFER_SIZE, 40 * DEFAULT_BUFFER_SIZE)
FAILING_CHANCE: Final[float] = 0.1
FAILING_READS: Final[Tuple[int, int]] = (1, 6)
SLOW_CHANCE: Final[float] = 0.1
SLOWEST_READ_SECONDS: Final[float] = 0.001
LONGEST_REST_SECONDS: Final[float] = 0.004
KEEP_DEVICE_CHANCE: Final[float] = 0.3
NOTHING_HELD: Final[str] = "no sound of its own to act on"


@dataclass(frozen=True)
class Stage:
    """What every owner of the storm acts on: the output, the machine under it, and the record kept of both."""

    output: AudioOutput
    system: FakeAudioSystem
    record: StormRecord


class StormOwner:
    """One thread of the storm: an owner starting sounds and acting on them, and on the output, at random.

    Each owner draws its actions from a generator seeded for it alone, so a seed names what every owner does,
    while the order their actions meet in is the machine's. An owner acts on the sounds it started, as every
    owner in the application holds its own playbacks, and on the output as a whole.
    """

    def __init__(self, name: str, *, seed: int, stage: Stage) -> None:
        self.name = name
        self._random = random.Random(seed)
        self._stage = stage
        self._soundings: List[Sounding] = []

    def act(self) -> None:
        operation = self._random.choices(list(WEIGHTS), weights=list(WEIGHTS.values()))[0]
        self._stage.record.log(self.name, operation.value, self._run(operation))

    def rest(self) -> None:
        time.sleep(self._random.uniform(0.0, LONGEST_REST_SECONDS))

    def claim_at_once(self) -> Tuple[int, Optional[Playback[StormMark]]]:
        """Claims the output for an endless sound at a random rank, beside the other owners claiming it too.

        Raises:
            NoOutputDeviceError: If no device is in force, which a quiesced output always has.
        """
        sound = StormSound(
            identity=self._stage.record.next_identity(),
            length=None,
            failing_read=None,
            read_seconds=0.0,
        )
        rank = self._random.choice(RANKS)
        playback = self._play(sound, rank)
        self._stage.record.log(self.name, "claim at once", self._claim_outcome(sound, rank, playback))
        return rank, playback

    def _run(self, operation: Operation) -> str:
        match operation:
            case Operation.PLAY:
                return self._play_drawn()
            case Operation.STOP:
                return self._on_held(lambda sounding: _answer(sounding.playback.stop(), "stopped"))
            case Operation.PAUSE:
                return self._on_held(lambda sounding: _answer(sounding.playback.pause(), "paused"))
            case Operation.RESUME:
                return self._on_held(lambda sounding: _answer(sounding.playback.resume(), "resumed"))
            case Operation.SEEK:
                return self._on_held(self._seek)
            case Operation.FAIL_ASIDE:
                return self._on_held(lambda sounding: _answer(sounding.source.fail_aside(), "told"))
            case Operation.STOP_ALL:
                self._stage.output.stop_all()
                return "asked"
            case Operation.CONFIGURE:
                return self._configure()
            case Operation.REFRESH:
                return self._refresh()
            case Operation.UNPLUG:
                self._stage.system.devices = [SPEAKERS]
                return self._refresh()
            case Operation.PLUG:
                self._stage.system.devices = [SPEAKERS, HEADPHONES]
                return self._refresh()

    def _play_drawn(self) -> str:
        sound = self._sound()
        rank = self._random.choice(RANKS)
        try:
            playback = self._play(sound, rank)
        except NoOutputDeviceError:
            return f"sound {sound.identity} refused, with no device in force"

        return self._claim_outcome(sound, rank, playback)

    def _play(self, sound: StormSound, rank: int) -> Optional[Playback[StormMark]]:
        listener = StormListener(sound, self._stage.system.timeline)
        source = StormSource(sound)
        playback = self._stage.output.play(source, rank=rank, listener=listener)
        if playback is not None:
            sounding = Sounding(playback=playback, listener=listener, source=source, rank=rank)
            self._soundings.append(sounding)
            self._stage.record.keep(sounding)

        return playback

    def _sound(self) -> StormSound:
        draw = self._random.random()
        length: Optional[int] = None
        if draw >= ENDLESS_CHANCE:
            length = self._random.randint(*(SHORT_FRAMES if draw < ENDLESS_CHANCE + SHORT_CHANCE else LONG_FRAMES))

        failing = self._random.random() < FAILING_CHANCE
        slow = self._random.random() < SLOW_CHANCE
        return StormSound(
            identity=self._stage.record.next_identity(),
            length=length,
            failing_read=self._random.randint(*FAILING_READS) if failing else None,
            read_seconds=self._random.uniform(0.0, SLOWEST_READ_SECONDS) if slow else 0.0,
        )

    def _on_held(self, action: Callable[[Sounding], str]) -> str:
        if not self._soundings:
            return NOTHING_HELD

        sounding = self._random.choice(self._soundings[-RECENT:])
        return f"sound {sounding.listener.sound.identity} {action(sounding)}"

    def _seek(self, sounding: Sounding) -> str:
        target = self._random.randrange(SEEK_RANGE)
        accepted = sounding.playback.command(partial(sounding.source.seek, target))
        if accepted:
            sounding.listener.sought(target)

        return _answer(accepted, f"sought to {target}")

    def _configure(self) -> str:
        record = self._stage.record
        device = record.settings.device
        if self._random.random() >= KEEP_DEVICE_CHANCE:
            catalog = record.catalog
            if not catalog.devices:
                return "found no device listed"

            index = self._random.choice(sorted(catalog.devices))
            device = catalog.configured(index, self._random.choice(catalog.devices[index].supported_sample_rates))

        settings = OutputSettings(device=device, buffer_size=self._random.choice(BUFFER_SIZES_TRIED))
        record.configured(settings)
        self._stage.output.configure(settings)
        named = "no device" if device is None else f"{device.name} at {device.sample_rate} Hz"
        return f"{named}, {settings.buffer_size} frames a buffer"

    def _refresh(self) -> str:
        self._stage.output.refresh(self._stage.record.refreshed)
        return f"asked, with {', '.join(device.name for device in self._stage.system.devices)} plugged in"

    @staticmethod
    def _claim_outcome(sound: StormSound, rank: int, playback: Optional[Playback[StormMark]]) -> str:
        length = "endless" if sound.length is None else f"{sound.length} frames"
        failing = "" if sound.failing_read is None else f", failing at read {sound.failing_read}"
        held = "declined" if playback is None else "held"
        return f"sound {sound.identity} ({length}{failing}) at rank {rank}: {held}"


def _answer(done: bool, what: str) -> str:
    return what if done else f"not {what}, having ended"
