from dataclasses import dataclass
from typing import Dict, Generic, List, Mapping, Optional, Tuple

from sampletones_core.audio.output.ending import EndCause
from sampletones_core.audio.output.lifecycle import (
    PlaybackLifecycle,
    PlaybackPhase,
    StreamAction,
    StreamLifecycle,
    StreamPhase,
)

from .reads import ReadKind, SourceRead
from .step import EndReport, KeyT, PlaybackSnapshot, SessionSnapshot, Step


@dataclass
class _Entry:
    lifecycle: PlaybackLifecycle
    rank: int
    commanded: bool


class SessionCore(Generic[KeyT]):
    """The output's decisions, made over every playback present and the one device stream.

    The render thread claims, commands and stops playbacks, and asks for new settings or a close. The
    thread writing to the device asks for its next step, runs it, and reports how the device answered. The
    core makes every decision those threads act on: which claim holds the output, what the writer does next,
    which playbacks a block mixes, whose positions a written block reports, and the one end report each
    playback sends. Its owner makes every device call and serializes every call to the core, so a case can
    drive every order of them on one thread.

    A claim ranked below a playback holding the output is declined, and any other claim takes the output
    from every playback holding it and starts on a stream of its own. An end report goes out at the step
    after the playback's end is decided, once the writer has taken the playback out of the sound. A sound
    that finished as the last one playing sends its report once its tail has played out and the stream has
    closed.

    A command, such as a seek, reaches a playback before the read after the step that mixes it. A command
    arriving while a block is read and written keeps a read that ran the sound out from finishing it, since
    the next read already plays from where the command moved the sound.
    """

    def __init__(self) -> None:
        self._stream = StreamLifecycle()
        self._entries: Dict[KeyT, _Entry] = {}

    @property
    def stream_phase(self) -> StreamPhase:
        return self._stream.phase

    @property
    def closing(self) -> bool:
        return self._stream.closing

    @property
    def is_sounding(self) -> bool:
        """Whether any playback holds the output, from its claim until its end is decided."""
        return any(entry.lifecycle.engaged for entry in self._entries.values())

    def is_engaged(self, key: KeyT) -> bool:
        entry = self._entries.get(key)
        return entry is not None and entry.lifecycle.engaged

    def is_paused(self, key: KeyT) -> bool:
        entry = self._entries.get(key)
        return entry is not None and entry.lifecycle.paused

    def ending(self) -> Tuple[KeyT, ...]:
        """The playbacks whose end is decided and whose report has yet to go out."""
        return tuple(key for key, entry in self._entries.items() if entry.lifecycle.phase is PlaybackPhase.ENDING)

    def phase_of(self, key: KeyT) -> Optional[PlaybackPhase]:
        """Where a playback present stands, or ``None`` once its end report has gone out."""
        entry = self._entries.get(key)
        return None if entry is None else entry.lifecycle.phase

    def snapshot(self) -> SessionSnapshot[KeyT]:
        return SessionSnapshot(
            stream=self._stream.state,
            playbacks=tuple(
                PlaybackSnapshot(
                    key=key,
                    rank=entry.rank,
                    state=entry.lifecycle.state,
                    commanded=entry.commanded,
                )
                for key, entry in self._entries.items()
            ),
        )

    def claim(self, key: KeyT, *, rank: int) -> bool:
        """Asks for the output for a new playback; answers whether the playback holds it.

        Raises:
            ValueError: If a playback under ``key`` is still present.
        """
        if key in self._entries:
            raise ValueError(f"A playback under {key!r} is still present")

        if self._stream.closing or any(
            entry.lifecycle.engaged and entry.rank > rank for entry in self._entries.values()
        ):
            return False

        for entry in self._entries.values():
            entry.lifecycle.displace()

        self._entries[key] = _Entry(lifecycle=PlaybackLifecycle(), rank=rank, commanded=False)
        self._stream.claimed()
        return True

    def stop(self, key: KeyT) -> bool:
        entry = self._entries.get(key)
        return entry is not None and entry.lifecycle.stop()

    def stop_all(self) -> None:
        for entry in self._entries.values():
            entry.lifecycle.stop()

    def pause(self, key: KeyT) -> bool:
        entry = self._entries.get(key)
        return entry is not None and entry.lifecycle.pause()

    def resume(self, key: KeyT) -> bool:
        entry = self._entries.get(key)
        return entry is not None and entry.lifecycle.resume()

    def accepts_commands(self, key: KeyT) -> bool:
        """Whether a seek or a replacement still reaches the playback."""
        entry = self._entries.get(key)
        return entry is not None and entry.lifecycle.accepts_commands()

    def command(self, key: KeyT) -> bool:
        """Takes a command for a playback, which reaches it before its next read; answers whether it still plays."""
        entry = self._entries.get(key)
        if entry is None or not entry.lifecycle.accepts_commands():
            return False

        entry.commanded = True
        return True

    def fail(self, key: KeyT, error: Exception) -> bool:
        """Ends a playback with a failure its source met between reads; answers whether the failure decided it."""
        entry = self._entries.get(key)
        return entry is not None and entry.lifecycle.fail(error)

    def reconfigure(self) -> bool:
        """Asks for new device settings, which end every playback present; answers whether the output takes them."""
        if not self._stream.request_reconfigure():
            return False

        self.stop_all()
        return True

    def close(self) -> None:
        """Closes the output for good: every playback present ends, and every later claim is declined."""
        self._stream.request_close()
        self.stop_all()

    def abandon(self) -> Tuple[EndReport[KeyT], ...]:
        """Ends every playback present at once, for a teardown that stopped waiting for the writer.

        The writer may still be inside a device call, so the reports go out from the caller's thread, and
        whatever the writer reports afterwards finds every playback ended.
        """
        self.close()
        reports = tuple(
            EndReport(key=key, ending=ending)
            for key, entry in self._entries.items()
            if (ending := entry.lifecycle.settle()) is not None
        )
        self._entries.clear()
        return reports

    def next_step(self) -> Step[KeyT]:
        """Settles the ends that are due and answers what the writer does next.

        A write takes the commands waiting for each playback it mixes, which the writer runs before the read.
        """
        mixing = [key for key, entry in self._entries.items() if entry.lifecycle.mixed]
        finished = any(self._ends_by(entry, EndCause.FINISHED) for entry in self._entries.values())
        action = self._stream.next_action(wanted=self.is_sounding, mixing=bool(mixing), tail=finished)
        reports = self._settle(keep_finished=action is StreamAction.DRAIN)
        mixed = tuple(mixing) if action is StreamAction.WRITE else ()
        for key in mixed:
            self._entries[key].commanded = False

        return Step(action=action, mixed=mixed, reports=reports)

    def opened(self) -> None:
        self._stream.opened()

    def open_failed(self, error: Exception) -> None:
        """The device refused the stream, which fails every playback holding the output."""
        for entry in self._entries.values():
            if entry.lifecycle.engaged:
                entry.lifecycle.fail(error)

    def wrote(self, reads: Mapping[KeyT, SourceRead]) -> Tuple[KeyT, ...]:
        """The device took a block; answers the playbacks whose positions for it go out.

        Args:
            reads: How each playback the block mixed answered its read.
        """
        positions: List[KeyT] = []
        for key, read in reads.items():
            entry = self._entries.get(key)
            if entry is None:
                continue

            if read.error is not None:
                entry.lifecycle.fail(read.error)
                continue

            if entry.lifecycle.written():
                positions.append(key)

            if read.kind is ReadKind.LAST and not entry.commanded:
                entry.lifecycle.finish()

        return tuple(positions)

    def write_failed(self, error: Exception, reads: Mapping[KeyT, SourceRead]) -> None:
        """The device failed a write, which fails every playback holding the output and breaks the stream.

        A playback whose own source failed for the block fails with its own error.
        """
        self._stream.write_failed()
        for key, entry in self._entries.items():
            read = reads.get(key)
            own_error = None if read is None else read.error
            entry.lifecycle.fail(error if own_error is None else own_error)

    def closed(self, error: Optional[Exception]) -> None:
        """The stream is closed, which fails a sound waiting for its tail where the device failed to play it out."""
        self._stream.closed()
        if error is None:
            return

        for entry in self._entries.values():
            if self._ends_by(entry, EndCause.FINISHED):
                entry.lifecycle.fail(error)

    def reconfigured(self) -> None:
        self._stream.reconfigured()

    def _settle(self, *, keep_finished: bool) -> Tuple[EndReport[KeyT], ...]:
        """Sends the end reports that are due and lets those playbacks go.

        A sound that finished keeps its report while its tail plays out, since the report names how the
        tail went.
        """
        reports: List[EndReport[KeyT]] = []
        for key, entry in list(self._entries.items()):
            if keep_finished and self._ends_by(entry, EndCause.FINISHED):
                continue

            ending = entry.lifecycle.settle()
            if ending is not None:
                reports.append(EndReport(key=key, ending=ending))

            if entry.lifecycle.phase is PlaybackPhase.ENDED:
                del self._entries[key]

        return tuple(reports)

    @staticmethod
    def _ends_by(entry: _Entry, cause: EndCause) -> bool:
        ending = entry.lifecycle.ending
        return entry.lifecycle.phase is PlaybackPhase.ENDING and ending is not None and ending.cause is cause
