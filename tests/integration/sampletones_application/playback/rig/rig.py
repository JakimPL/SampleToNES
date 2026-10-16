import contextlib
import time
from functools import partial
from pathlib import Path
from typing import Callable, Final, FrozenSet, Iterator, List, Optional, Sequence

import numpy as np
import pytest

from sampletones_application.layout.behavior.scheduling.scheduling import SchedulingBehavior
from sampletones_application.logic.shared.live import Keyboard, LiveKey
from sampletones_application.logic.shared.playback_priority import PlaybackPriority
from sampletones_application.view_model.shared.audio_data import AudioData
from sampletones_core.audio.io import write_wave
from sampletones_core.constants.audio import BufferSize, SampleRate
from sampletones_shared.types.callback import VoidCallback
from tests.suite.application import draw_frame
from tests.suite.audio.machine import FakeAudioSystem
from tests.suite.audio.ramp import ramp_indices
from tests.suite.audio.timeline import Timeline, TimelineEvent, Written

from .errors import ErrorLog
from .hearing import Hearing
from .reports import End, EndCause, Mark, RowMark, Told, Wait
from .song import ScriptedSong
from .sound import BUFFERS, SOURCES, Sound
from .threads import ThreadWatch
from .wiring import PlaybackStack

WAIT_SECONDS: Final[float] = 10.0
POLL_SECONDS: Final[float] = 0.002
DRAIN_FRAMES: Final[int] = 3
PLAYED_KEY: Final[int] = 60
FILE_STEM: Final[str] = "preview"
FILE_SUFFIX: Final[str] = ".wav"
SHORT_DEADLINE_SECONDS: Final[float] = 0.05


class PlaybackRig:
    """The application's playback, driven the way a reader drives it, on a fake machine a case controls.

    The verbs are the gestures a reader makes on the render thread: playing, seeking, pausing and stopping a
    source, previewing a file or a voice, auditioning an instrument, pressing and lifting a key played live,
    the transport's Stop, a device change, a buffer size, a refresh, and the teardown. The readouts are what each owner heard once a drain delivered
    it, what the device received, and what the render thread waited for.

    A case reads outcomes alone. ``wait_for`` drains the queue until a condition holds and fails with the
    whole picture once ``WAIT_SECONDS`` pass, which guards against a hang and measures nothing.
    """

    def __init__(
        self,
        system: FakeAudioSystem,
        *,
        directory: Path,
        scheduling: SchedulingBehavior,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        self.system = system
        self.timeline: Timeline = system.timeline
        self.threads = ThreadWatch(monkeypatch)
        self.errors = ErrorLog()
        self.errors.attach()
        self.expects_errors: bool = False
        self._directory = directory
        self._files: int = 0
        self._torn_down: bool = False
        self.hearing = Hearing(
            holding=self._holding,
            open_streams=self._open_streams,
            written=self._written,
        )
        self.stack = PlaybackStack(system, hearing=self.hearing, profile=directory, scheduling=scheduling)

    @property
    def song(self) -> ScriptedSong:
        return self.stack.song

    def expect_errors(self) -> None:
        """Lets the after-check accept the errors the application logs, for a case that fails something on purpose."""
        self.expects_errors = True

    def shorten_deadlines(self) -> None:
        """Gives the teardown's wait on the audio threads ``SHORT_DEADLINE_SECONDS``, for a case wedging a thread on
        purpose."""
        self.stack.teardown_seconds = SHORT_DEADLINE_SECONDS

    def load(self, sound: Sound, audio: np.ndarray, *, sample_rate: int) -> None:
        """Gives a player its audio, which replaces the audio of a playback under way, or writes the file a preview reads."""
        with self._gesture():
            match sound:
                case Sound.RECONSTRUCTION | Sound.INSTRUCTION:
                    self.stack.player(sound).load_audio_data(AudioData.from_array(audio, sample_rate))
                case Sound.FILE:
                    self.stack.file = self._write_file(audio, sample_rate)
                case _:
                    raise ValueError(f"The {sound.value} plays what it renders itself")

    def compose(self, orders: Sequence[Sequence[int]]) -> None:
        """Gives the song its orders, each a sequence of row lengths in samples."""
        self.song.compose(orders)

    def focus(self, sound: Optional[Sound]) -> None:
        """Brings the tab whose source is ``sound`` to the front, or a tab with no source of its own."""
        self.stack.active = sound

    def hold_keys(self, held: bool) -> None:
        """Whether a key :meth:`play` presses stays down until the case lifts it, or is tapped and let go at once."""
        self.stack.keys_held = held

    def press(self, number: int, *, keyboard: Keyboard) -> None:
        """Presses a key played live, as its keyboard hands it over."""
        with self._gesture():
            self.stack.keys.key_down(self.stack.strike(keyboard, number))

    def lift(self, number: int, *, keyboard: Keyboard) -> None:
        with self._gesture():
            self.stack.keys.key_up(LiveKey(keyboard=keyboard, number=number))

    def pedal(self, down: bool) -> None:
        with self._gesture():
            self.stack.keys.pedal(down)

    def play(self, sound: Sound) -> None:
        """Plays a sound on the reader's request: a source from its start, a voice or a file at once, or a key played
        live, held or tapped as :meth:`hold_keys` says."""
        if sound is Sound.KEYS:
            self.press(PLAYED_KEY, keyboard=Keyboard.MIDI)
            if not self.stack.keys_held:
                self.lift(PLAYED_KEY, keyboard=Keyboard.MIDI)

            return

        with self._gesture():
            match sound:
                case Sound.RECONSTRUCTION | Sound.INSTRUCTION | Sound.SONG:
                    self.stack.guards[sound].play()
                case Sound.VOICE:
                    self.stack.voices.play_voice(self.stack.instrument.id)
                case Sound.FILE:
                    self.stack.files.play(self._file())

    def autoplay(self, sound: Sound) -> None:
        """Previews a voice or a file the way picking it with autoplay on does."""
        match sound:
            case Sound.VOICE:
                if not self.stack.session_manager.autoplay:
                    self.stack.session_manager.toggle_autoplay()

                with self._gesture():
                    self.stack.voices.request_autoplay(self.stack.instrument.id)

                self.drain()
            case Sound.FILE:
                with self._gesture():
                    self.stack.files.play_at(self._file(), PlaybackPriority.PREVIEW)
            case _:
                raise ValueError(f"The {sound.value} is a source, which a reader plays")

    def seek(self, sound: Sound, position: int) -> None:
        """Clicks a waveform at a sample, which moves an engaged player there and starts an idle one there."""
        if sound not in BUFFERS:
            raise ValueError(f"The {sound.value} draws no waveform its player sounds")

        with self._gesture():
            self.stack.guards[sound].run_guarded(partial(self.stack.player(sound).play_from, position))

    def seek_order(self, order_position: int) -> None:
        """Picks another order while the song plays, which moves the playhead there."""
        with self._gesture():
            self.stack.song_player.seek(order_position)

    def pause_or_resume(self, sound: Sound) -> None:
        with self._gesture():
            self.stack.guards[sound].pause_or_resume()

    def stop(self, sound: Sound) -> None:
        """Stops one source the way its own tab does."""
        with self._gesture():
            self.stack.guards[sound].stop()

    def stop_all(self) -> None:
        """The transport's Stop."""
        with self._gesture():
            self.stack.router.stop()

    def change_device(self, device_index: int, *, sample_rate: SampleRate) -> None:
        """Applies the Audio settings dialog's device and rate."""
        with self._gesture():
            self.stack.change_device(device_index, sample_rate=sample_rate)

    def set_buffer_size(self, frames: BufferSize) -> None:
        with self._gesture():
            self.stack.set_buffer_size(frames)

    def refresh(self) -> None:
        """The Audio settings dialog's Refresh."""
        with self._gesture():
            self.stack.refresh()

    def teardown(self) -> None:
        """Quits the way the application does: every sound stops, then the output closes."""
        if self._torn_down:
            return

        self._torn_down = True
        with self.hearing.gesture():
            self.stack.teardown()

    def on_end(self, sound: Sound, action: VoidCallback) -> None:
        """Runs ``action`` on the render thread each time ``sound``'s owner hears an end."""
        self.hearing.on_end(sound, action)

    def marks(self, sound: Sound) -> List[Mark]:
        return self.hearing.log(sound).marks

    def positions(self, sound: Sound) -> List[int]:
        return [mark.position for mark in self.marks(sound)]

    @property
    def rows(self) -> List[RowMark]:
        return self.hearing.rows

    def ends(self, sound: Sound) -> List[End]:
        return self.hearing.log(sound).ends

    def causes(self, sound: Sound) -> List[Optional[EndCause]]:
        return [end.cause for end in self.ends(sound)]

    def engaged(self, sound: Sound) -> bool:
        return self.stack.guards[sound].is_engaged()

    @property
    def stop_available(self) -> bool:
        return self.stack.router.is_stop_enabled

    @property
    def told(self) -> List[Told]:
        return self.hearing.told

    @property
    def waits(self) -> List[Wait]:
        return self.threads.waits

    def written(self) -> np.ndarray:
        """The document indices the device received, read back from the ramp, in the order it played them."""
        return ramp_indices(self.timeline.written())

    def drain(self) -> None:
        """Draws frames until what the threads have reported so far has reached its owners."""
        with self.hearing.delivering():
            for _ in range(DRAIN_FRAMES):
                draw_frame()

    def wait_for(self, condition: Callable[[], bool], *, what: str) -> None:
        """Drains the queue until ``condition`` holds.

        Raises:
            AssertionError: If ``WAIT_SECONDS`` pass first, naming ``what`` and the whole picture.
        """
        deadline = time.monotonic() + WAIT_SECONDS
        while True:
            self.drain()
            if condition():
                return

            if time.monotonic() > deadline:
                raise AssertionError(f"Waited in vain for {what}\n{self.describe()}")

            time.sleep(POLL_SECONDS)

    def wait_for_device(self, condition: Callable[[], bool], *, what: str) -> None:
        """Waits until ``condition`` holds while the render thread takes nothing, so every report stays queued.

        Raises:
            AssertionError: If ``WAIT_SECONDS`` pass first, naming ``what`` and the whole picture.
        """
        deadline = time.monotonic() + WAIT_SECONDS
        while not condition():
            if time.monotonic() > deadline:
                raise AssertionError(f"Waited in vain for {what}\n{self.describe()}")

            time.sleep(POLL_SECONDS)

    def wait_until_written(self, samples: int) -> None:
        self.wait_for(lambda: len(self.timeline.written()) >= samples, what=f"{samples} samples written")

    def settle(self) -> None:
        """Waits until the device holds no stream and every audio thread has ended, then drains what they reported."""
        self.wait_for(
            lambda: not self.timeline.open_streams() and not self.threads.audio_threads(),
            what="the device to fall quiet",
        )

    def describe(self) -> str:
        """The whole picture, for a failing case to print: the device's timeline, then what each owner heard."""
        lines = ["timeline:"]
        lines.extend(f"  {_describe_event(event)}" for event in self.timeline.events())
        for sound in Sound:
            log = self.hearing.log(sound)
            if log.marks or log.ends:
                lines.append(f"{sound.value}: marks={[mark.position for mark in log.marks]} ends={log.ends}")

        if self.rows:
            lines.append(f"rows: {[(row.position.order_position, row.position.row_index) for row in self.rows]}")

        lines.append(f"told: {self.told}")
        lines.append(f"waits: {self.waits}")
        lines.append(f"errors: {self.errors.messages}")
        return "\n".join(lines)

    @contextlib.contextmanager
    def _gesture(self) -> Iterator[None]:
        with self.hearing.gesture(), self.threads.watching_waits():
            yield

    def _holding(self, sound: Sound) -> bool:
        return sound in SOURCES and self.engaged(sound)

    def _open_streams(self) -> FrozenSet[int]:
        return frozenset(self.timeline.open_streams())

    def _written(self) -> int:
        return len(self.timeline.written())

    def _file(self) -> Path:
        if self.stack.file is None:
            raise ValueError("No file was written for a preview to read")

        return self.stack.file

    def _write_file(self, audio: np.ndarray, sample_rate: int) -> Path:
        self._files += 1
        path = self._directory / f"{FILE_STEM}{self._files}{FILE_SUFFIX}"
        write_wave(path, sample_rate, audio)
        return path


def _describe_event(event: TimelineEvent) -> str:
    """One event as a line, a write shown by the span of indices it carried in place of its samples."""
    if not isinstance(event, Written):
        return repr(event)

    indices = ramp_indices(event.samples)
    span = f"{indices[0]}..{indices[-1]}" if len(indices) else "empty"
    return f"Written(stream={event.stream}, frames={len(indices)}, indices={span}, thread={event.thread})"
