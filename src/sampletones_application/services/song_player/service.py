from functools import partial
from typing import Callable, List, Optional

from sampletones_application.services.song_player.result import (
    SongPlaybackEnded,
    SongPlayerResult,
    SongPositionUpdate,
)
from sampletones_application.services.song_player.source import SongSource, SynthesizerFactory
from sampletones_core.audio.output import AudioOutput, Ending, Playback
from sampletones_core.project.song_position import SongPosition
from sampletones_shared.logger import logger

SongResultHandler = Callable[[SongPlayerResult], None]


class SongPlayerService:
    """Plays the song through the audio output, one playback for each start.

    Each start builds a source that renders the song ahead of the device on a thread of its own, at the
    rate of the stream it plays on, and claims the output at ``output_priority``. The song holds the output
    from that claim, so a sound ranked below it is declined for the whole span, the moments before its
    stream opens included.

    The service is its playback's listener, and its subscribers hear on the render thread every row the
    device took, in order, and then the one end report: the song finished, its player stopped it, another
    sound took the output, or it failed. A report of a song the service has let go of reaches nobody.
    """

    def __init__(
        self,
        output: AudioOutput,
        synthesizer_factory: SynthesizerFactory,
        *,
        should_loop: Callable[[], bool],
        master_gain: Callable[[], float],
        output_priority: int,
    ) -> None:
        self._output = output
        self._synthesizer_factory = synthesizer_factory
        self._should_loop = should_loop
        self._master_gain = master_gain
        self._output_priority = output_priority
        self._playback: Optional[Playback[SongPosition]] = None
        self._source: Optional[SongSource] = None
        self._handlers: List[SongResultHandler] = []

    @property
    def alive(self) -> bool:
        """Whether the song holds the output, from its claim in :meth:`start` until its end is decided."""
        return self._playback is not None and self._playback.engaged

    @property
    def is_playing(self) -> bool:
        return self._playback is not None and self._playback.engaged and not self._playback.paused

    @property
    def is_paused(self) -> bool:
        return self._playback is not None and self._playback.engaged and self._playback.paused

    def subscribe(self, handler: SongResultHandler) -> None:
        self._handlers.append(handler)

    def start(
        self,
        *,
        order_position: int,
        row_index: int,
    ) -> None:
        """Starts the song at a row, stopping the song this service plays.

        A claim the output declines starts nothing.

        Raises:
            NoOutputDeviceError: If no output device is in force.
        """
        self._let_go()
        source = SongSource(
            self._synthesizer_factory,
            start=SongPosition(order_position=order_position, row_index=row_index),
            should_loop=self._should_loop,
            master_gain=self._master_gain,
            threads=self._output.threads,
        )
        playback = self._output.play(source, rank=self._output_priority, listener=self)
        if playback is None:
            logger.info("SongPlayerService: the output is held above the song; start declined")
            return

        self._playback, self._source = playback, source

    def stop(self) -> None:
        self._let_go()

    def pause(self) -> None:
        if self._playback is not None:
            self._playback.pause()

    def resume(self) -> None:
        if self._playback is not None:
            self._playback.resume()

    def seek(self, order_position: int) -> None:
        """Moves the live playhead to another order while playback continues.

        This keeps the synthesizer's state, so voices sounding at the moment of the move carry over to the
        new order: the playhead jumps while the audio plays on. Rows already rendered ahead play out first,
        so the jump lands within one look-ahead window.
        """
        if self._playback is not None and self._source is not None:
            self._playback.command(partial(self._source.seek, order_position))

    def relocate(self, order_position: int) -> None:
        """Repoints the playhead at another order while keeping the current row.

        Used to follow a structural order edit (insert/remove/move) so playback stays on the frame it was
        sounding: the row within the frame continues from where it was, and voices carry over.
        """
        if self._playback is not None and self._source is not None:
            self._playback.command(partial(self._source.relocate, order_position))

    def positioned(self, playback: Playback[SongPosition], report: SongPosition) -> None:
        if playback is self._playback:
            self._emit(SongPositionUpdate(position=report))

    def ended(self, playback: Playback[SongPosition], ending: Ending) -> None:
        if playback is not self._playback:
            return

        self._playback, self._source = None, None
        self._emit(SongPlaybackEnded(ending=ending))

    def _let_go(self) -> None:
        """Stops the song held and lets it go, so its end report reaches nobody."""
        playback, self._playback, self._source = self._playback, None, None
        if playback is not None:
            playback.stop()

    def _emit(self, result: SongPlayerResult) -> None:
        for handler in list(self._handlers):
            handler(result)
