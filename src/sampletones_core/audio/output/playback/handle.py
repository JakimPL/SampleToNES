import threading
from functools import partial
from typing import Generic, List, Tuple

import numpy as np

from sampletones_core.audio.output.ending import Ending
from sampletones_core.audio.output.source import AudioSource, ReportT, Tagged
from sampletones_shared.types.callback import VoidCallback

from .feed import PlaybackControl
from .listener import PlaybackListener, Post


class Playback(Generic[ReportT]):
    """One sound on the output, from its claim until its end report, as the owner that started it holds it.

    The owner pauses, resumes, stops and commands the sound here, and hears of it through its listener:
    every position the device took, in order, and then one end report naming why it ended. A command
    reaches the source on the writer's thread before its next read, and a position read before the
    owner's latest command is dropped as it lands, so a mark drawn after a seek reads the seek.

    Every report crosses to the owner's thread through ``post``, and the playback sends no position once it
    has sent its end. A position that lands after the end report is dropped as it lands, so the owner hears
    the end last, whichever thread sends it and however ``post`` delivers.
    """

    def __init__(
        self,
        source: AudioSource[ReportT],
        *,
        listener: PlaybackListener[ReportT],
        post: Post,
        control: PlaybackControl,
    ) -> None:
        """Holds what the playback sounds and who hears of it.

        Args:
            source: What the playback reads its sound from.
            listener: The owner, which hears the positions and the end report.
            post: Carries a report to the owner's thread.
            control: The output the playback plays on.
        """
        self._source = source
        self._listener = listener
        self._post = post
        self._control = control
        self._lock = threading.Lock()
        self._kept: List[VoidCallback] = []
        self._accepted: int = 0
        self._ended: bool = False
        self._end_delivered: bool = False
        self._due: List[VoidCallback] = []
        self._stamp: int = 0
        self._begun: bool = False
        self._read: Tuple[Tagged[ReportT], ...] = ()

    @property
    def engaged(self) -> bool:
        """Whether the playback holds the output, from its claim until its end is decided."""
        return self._control.is_engaged(self)

    @property
    def paused(self) -> bool:
        return self._control.is_paused(self)

    def pause(self) -> bool:
        """Holds the sound where it stands; answers whether it still played."""
        return self._control.pause(self)

    def resume(self) -> bool:
        """Lets a held sound play on; answers whether it still played."""
        return self._control.resume(self)

    def stop(self) -> bool:
        """Ends the sound at once; answers whether the stop decided its end."""
        return self._control.stop(self)

    def command(self, action: VoidCallback) -> bool:
        """Runs ``action`` on the writer's thread before the next read, such as a seek of the source.

        Returns:
            bool: Whether the playback still plays, which a playback whose end is decided answers ``False``
                to, so its owner starts a new one.
        """
        return self._control.command(self, action)

    def enqueue(self, action: VoidCallback) -> None:
        with self._lock:
            self._kept.append(action)
            self._accepted += 1

    def take_commands(self) -> None:
        with self._lock:
            self._due.extend(self._kept)
            self._kept = []
            self._stamp = self._accepted

    def read_into(self, block: np.ndarray, *, output_rate: int) -> int:
        if not self._begun:
            self._begun = True
            self._source.begin(output_rate, self._failed)

        due, self._due = self._due, []
        for action in due:
            action()

        fill = self._source.read_into(block)
        self._read = fill.reports
        return fill.frames

    def heard(self) -> None:
        reports, self._read = self._read, ()
        with self._lock:
            if self._ended:
                return

            stamp = self._stamp

        for tagged in reports:
            self._post(partial(self._deliver_position, tagged.report, stamp))

    def end(self, ending: Ending) -> None:
        with self._lock:
            if self._ended:
                return

            self._ended = True

        self._post(partial(self._deliver_end, ending))

    def close(self) -> None:
        self._source.close()

    def _failed(self, error: Exception) -> None:
        self._control.fail(self, error)

    def _deliver_position(self, report: ReportT, stamp: int) -> None:
        """Hands a position to the listener, unless a command came after the read that made it or the end landed."""
        with self._lock:
            current = stamp == self._accepted and not self._end_delivered

        if current:
            self._listener.positioned(self, report)

    def _deliver_end(self, ending: Ending) -> None:
        with self._lock:
            self._end_delivered = True

        self._listener.ended(self, ending)
