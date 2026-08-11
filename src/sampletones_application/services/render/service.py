import threading
from functools import partial
from pathlib import Path

from sampletones_application.services.base import ServiceBase
from sampletones_application.services.render.progress import StageProgress
from sampletones_application.services.render.result import RenderResult, RenderStage
from sampletones_application.services.render.sink import (
    EncodeReporter,
    RenderSink,
    build_render_sink,
)
from sampletones_application.services.result import (
    ServiceCancelled,
    ServiceError,
    ServiceStarted,
    ServiceSuccess,
)
from sampletones_application.services.synthesis.protocol import RowSynthesizerProtocol
from sampletones_application.utils.parallelization.thread import SingleThreadExecutor
from sampletones_core.audio.writers import AudioOutputSpec
from sampletones_shared.logger import logger


class SongRenderService(ServiceBase[RenderResult]):
    """Renders a whole song to a file on a background thread, reporting each pass as it runs.

    The synthesiser arrives per call, so the service holds no opinion on what a song sounds
    like: it drives the same kernel the player drives, one row at a time, and hands each row to
    a sink. The sink decides what becomes of a row — straight to the encoder, or spilled and
    written back at the level the whole render turned out to reach — so the service reports one
    pass or two without knowing which format waits on the other side.

    A render is one at a time. Cancelling is honoured between rows and between encoded blocks,
    and the file a cancelled or failed run was writing is removed, so a result names a path only
    where a finished file stands.
    """

    def __init__(self, priority: int = 0) -> None:
        super().__init__(priority)
        self._executor = SingleThreadExecutor()
        self._cancel_event = threading.Event()
        self._running = threading.Event()

    def start(
        self,
        *,
        synthesizer: RowSynthesizerProtocol,
        destination: Path,
        spec: AudioOutputSpec,
        normalize: bool,
        total_samples: int,
    ) -> bool:
        """Begins a render on the worker thread; reports whether it took the request.

        Args:
            synthesizer: The kernel the song is rendered through, from its first row.
            destination: Where the finished file is written.
            spec: The format, rate, and quality it is written at.
            normalize: Whether the render is scaled so its loudest sample reaches full scale.
            total_samples: The samples the whole song holds, which the passes are measured against.

        Returns:
            bool: Whether a render started; a request arriving while one runs is declined.
        """
        if self.is_running():
            logger.warning(f"{self.class_name}: a render is already running; start ignored")
            return False

        self._cancel_event.clear()
        self._running.set()
        sink = build_render_sink(destination, spec, normalize=normalize)
        started = self._executor.execute(
            partial(self._run, synthesizer, sink, total_samples),
            wait=False,
        )
        if not started:
            self._running.clear()

        return started

    def cancel(self) -> None:
        """Asks a running render to stop at its next row or block."""
        self._cancel_event.set()

    def is_running(self) -> bool:
        return self._running.is_set()

    def shutdown(self) -> None:
        """Winds a running render down for application exit.

        The worker runs on a :class:`SingleThreadExecutor`, so the teardown that joins every
        background worker reaches this one; asking it to stop first is what keeps that join short.
        """
        self._cancel_event.set()

    def _run(
        self,
        synthesizer: RowSynthesizerProtocol,
        sink: RenderSink,
        total_samples: int,
    ) -> None:
        try:
            self._emit(ServiceStarted(total=total_samples))
            self._report_outcome(sink, self._render(synthesizer, sink, total_samples))
        except Exception as exception:  # pylint: disable=broad-exception-caught
            logger.error_with_traceback(exception, f"{self.class_name}: failed to render to {sink.destination}")
            sink.discard()
            self._emit(ServiceError(exception=exception))
        finally:
            self._running.clear()

    def _render(
        self,
        synthesizer: RowSynthesizerProtocol,
        sink: RenderSink,
        total_samples: int,
    ) -> bool:
        with sink:
            if not self._synthesize(synthesizer, sink, total_samples):
                return False

            return sink.finish(self._encode_reporter(total_samples))

    def _synthesize(
        self,
        synthesizer: RowSynthesizerProtocol,
        sink: RenderSink,
        total_samples: int,
    ) -> bool:
        """Renders the song from its first row into the sink; reports whether it reached the end.

        The song is rendered as the document holds it, from the top: the position a listener left
        the playhead at is a listening choice, and a render describes the whole song.
        """
        progress = StageProgress(RenderStage.SYNTHESIS, total_samples, emit=self._emit)
        synthesizer.set_position(0, 0)
        synthesizer.reset()

        rendered = 0
        while not synthesizer.is_finished:
            if self._cancel_event.is_set():
                return False

            chunk, _ = synthesizer.render_row()
            sink.write(chunk)
            rendered = min(total_samples, rendered + len(chunk))
            progress.advance(rendered)

        return not self._cancel_event.is_set()

    def _encode_reporter(self, total_samples: int) -> EncodeReporter:
        progress = StageProgress(RenderStage.ENCODING, total_samples, emit=self._emit)
        return partial(self._report_encoded, progress)

    def _report_encoded(self, progress: StageProgress, encoded: int) -> bool:
        progress.advance(encoded)
        return not self._cancel_event.is_set()

    def _report_outcome(self, sink: RenderSink, completed: bool) -> None:
        if not completed:
            sink.discard()
            self._emit(ServiceCancelled())
            return

        logger.info(f"Rendered the song to: {logger.format_path(sink.destination)}")
        self._emit(ServiceSuccess(value=sink.destination))
