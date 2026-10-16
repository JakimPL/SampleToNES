import threading
from functools import partial
from typing import Callable, List, Optional

import numpy as np

from sampletones_application.services.song_player.constants import PREFETCH_SECONDS, RENDERER_NAME
from sampletones_application.services.synthesis.protocol import RowSynthesizerProtocol
from sampletones_core.audio.output import AudioThreads, Fill, PrefetchBuffer
from sampletones_core.audio.output.source import FailureReport
from sampletones_core.project.song_position import SongPosition
from sampletones_shared.logger import logger

SynthesizerFactory = Callable[[int], RowSynthesizerProtocol]
SongMove = Callable[[RowSynthesizerProtocol], None]


class SongSource:
    """A song rendered row by row ahead of the device, on a thread of its own, and read in blocks.

    The source begins once the stream it plays on opens: it builds a synthesizer for the stream's rate and
    renders rows into a buffer holding ``PREFETCH_SECONDS`` of audio, which absorbs the synthesis's jitter so
    the device stays fed. Each row reports the position it played once the device has taken its last
    sample. A seek or a relocation reaches the synthesizer between rows, so rows already rendered ahead
    play out first and the jump lands within one look-ahead window, with the voices sounding carried over.
    Every block plays at the master gain read as the device asks for it, so a change is heard from the
    next block.

    The render thread starts through the output's registry, so a teardown waits for it. A synthesis that
    fails however its code fails ends the rows and ends the playback at once with the failure, sounding or
    held paused, and a read reaching the end of the rows raises it as well.
    """

    def __init__(
        self,
        synthesizer_factory: SynthesizerFactory,
        *,
        start: SongPosition,
        should_loop: Callable[[], bool],
        master_gain: Callable[[], float],
        threads: AudioThreads,
    ) -> None:
        """Holds what the song is rendered from and where it starts.

        Args:
            synthesizer_factory: Builds the synthesizer for the rate of the stream the song plays on.
            start: The row the song starts at.
            should_loop: Whether the song starts over once it reaches its end, read as it gets there.
            master_gain: The gain the song plays at, read for every block.
            threads: The registry the render thread starts through.
        """
        self._factory = synthesizer_factory
        self._start = start
        self._should_loop = should_loop
        self._master_gain = master_gain
        self._threads = threads
        self._lock = threading.Lock()
        self._moves: List[SongMove] = []
        self._closed: bool = False
        self._buffer: Optional[PrefetchBuffer[SongPosition]] = None
        self._failure: Optional[Exception] = None

    def begin(self, output_rate: int, failed: FailureReport) -> None:
        """Starts rendering for a stream taking ``output_rate`` samples a second, telling ``failed`` of a failure."""
        buffer: PrefetchBuffer[SongPosition] = PrefetchBuffer(capacity=max(1, round(PREFETCH_SECONDS * output_rate)))
        with self._lock:
            self._buffer = buffer
            closed = self._closed

        if closed:
            buffer.close()
            return

        self._threads.start(partial(self._render, buffer, output_rate, failed), name=RENDERER_NAME)

    def read_into(self, block: np.ndarray) -> Fill[SongPosition]:
        """Fills ``block`` from the rows rendered, waiting for them while the synthesis is behind.

        Raises:
            Exception: Whatever the synthesis failed with, at the first read the rows rendered before it
                leave short.
        """
        taken = self._require_buffer().take_into(block)
        if taken.closed:
            return Fill(frames=0, reports=())

        if taken.frames < len(block) and self._failure is not None:
            raise self._failure

        block[: taken.frames] *= np.float32(self._master_gain())
        return Fill(frames=taken.frames, reports=taken.reports)

    def seek(self, order_position: int) -> None:
        """Moves the song to the start of another order, keeping the voices sounding."""
        self._move(lambda synthesizer: synthesizer.set_position(order_position, 0))

    def relocate(self, order_position: int) -> None:
        """Repoints the song at another order on the row it stands at, following a structural order edit."""
        self._move(lambda synthesizer: synthesizer.set_position(order_position, synthesizer.row_index))

    def close(self) -> None:
        """Ends the song: the render thread stops at its next row, and a read waiting for one wakes."""
        with self._lock:
            self._closed = True
            buffer = self._buffer

        if buffer is not None:
            buffer.close()

    def _move(self, move: SongMove) -> None:
        with self._lock:
            self._moves.append(move)

    def _render(self, buffer: PrefetchBuffer[SongPosition], output_rate: int, failed: FailureReport) -> None:
        """Renders rows until the song ends or the buffer closes, handing a failure on to the playback."""
        try:
            self._render_rows(buffer, self._factory(output_rate))
        except Exception as exception:  # pylint: disable=broad-exception-caught
            logger.error_with_traceback(exception, "The song's synthesis failed")
            self._failure = exception
            buffer.end()
            failed(exception)

    def _render_rows(self, buffer: PrefetchBuffer[SongPosition], synthesizer: RowSynthesizerProtocol) -> None:
        synthesizer.set_position(self._start.order_position, self._start.row_index)
        synthesizer.reset()
        while True:
            self._apply_moves(synthesizer)
            if synthesizer.is_finished and not self._loop_to_start(synthesizer):
                buffer.end()
                return

            chunk, position = synthesizer.render_row()
            if not buffer.put(chunk, position):
                return

    def _apply_moves(self, synthesizer: RowSynthesizerProtocol) -> None:
        with self._lock:
            moves, self._moves = self._moves, []

        for move in moves:
            move(synthesizer)

    def _loop_to_start(self, synthesizer: RowSynthesizerProtocol) -> bool:
        """Wraps the song back to its start where looping is on; answers whether it looped.

        A song with no orders stays finished after the wrap, so it ends there. The channels start clean, as a
        fresh start leaves them.
        """
        if not self._should_loop():
            return False

        synthesizer.set_position(0, 0)
        if synthesizer.is_finished:
            return False

        synthesizer.reset()
        return True

    def _require_buffer(self) -> PrefetchBuffer[SongPosition]:
        if self._buffer is None:
            raise RuntimeError("The song was read before the stream it plays on began it")

        return self._buffer
