from functools import partial
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from sampletones_core.audio.catalog import DeviceCatalog
from sampletones_core.audio.driver import OutputStreamProtocol
from sampletones_core.audio.output.arbiter import OutputArbiter
from sampletones_core.audio.output.backend import AudioBackend
from sampletones_core.audio.output.lifecycle import StreamAction
from sampletones_core.audio.output.playback import PlaybackFeed, Post
from sampletones_core.audio.output.session import (
    EndReport,
    SourceRead,
    mixed_block,
)
from sampletones_core.audio.processing import silence
from sampletones_shared.exceptions import NoOutputDeviceError, PlaybackError
from sampletones_shared.logger import logger


class StreamSession:
    """The thread writing to the device, for one run: from the step a request started it at until nothing is left.

    It asks the arbiter for each step and makes the device call that step names. It opens the stream on the
    device in force, reads one block from each playback the step mixes, sums them, and hands the device as
    many frames as the longest of them filled, so a sound ends on its last sample. A natural end plays the
    tail out, any other closes the stream at once, and a refresh renews the backend while no stream is open.
    Every device call runs outside the arbiter's lock, so a device slow to answer holds this thread alone.

    A source fails however its code fails, so its read is caught whole, and the failure ends that playback
    and leaves the others playing.
    """

    def __init__(self, arbiter: OutputArbiter, backend: AudioBackend, *, post: Post) -> None:
        self._arbiter = arbiter
        self._backend = backend
        self._post = post
        self._stream: Optional[OutputStreamProtocol] = None
        self._output_rate: int = 0
        self._block_frames: int = 0

    def run(self) -> None:
        while True:
            step = self._arbiter.next_step()
            self._report(step.reports)
            match step.action:
                case StreamAction.OPEN:
                    self._open()
                case StreamAction.WRITE:
                    self._write(step.mixed)
                case StreamAction.DRAIN:
                    self._drain()
                case StreamAction.ABORT:
                    self._abort()
                case StreamAction.RECONFIGURE:
                    self._reconfigure()
                case StreamAction.WAIT:
                    continue
                case StreamAction.EXIT:
                    return

    @staticmethod
    def _report(reports: Sequence[EndReport[PlaybackFeed]]) -> None:
        for report in reports:
            report.key.end(report.ending)
            report.key.close()

    def _open(self) -> None:
        settings = self._arbiter.settings
        if settings.device is None:
            self._arbiter.open_failed(NoOutputDeviceError("No audio output device is in force"))
            return

        try:
            stream = self._backend.driver.open_output(
                device_index=settings.device.device_index,
                sample_rate=settings.device.sample_rate,
                frames_per_buffer=settings.buffer_size,
            )
        except OSError as exception:
            failure = PlaybackError(f"Failed to open audio stream: {exception}")
            logger.error_with_traceback(failure, "The device refused the audio stream")
            self._arbiter.open_failed(failure)
            return

        self._stream = stream
        self._output_rate = settings.device.sample_rate
        self._block_frames = settings.buffer_size
        logger.debug(f"Audio stream opened at {self._output_rate} Hz on device {settings.device.device_index}")
        self._arbiter.opened()

    def _write(self, mixed: Sequence[PlaybackFeed]) -> None:
        reads, fills = self._read(mixed)
        frames = max((len(samples) for samples in fills), default=0)
        if frames:
            try:
                self._require_stream().write(mixed_block(fills, frames).tobytes())
            except OSError as exception:
                failure = PlaybackError(f"Failed to write to audio stream: {exception}")
                logger.error_with_traceback(failure, "The device failed a write to the audio stream")
                self._arbiter.write_failed(failure, reads)
                return

        for feed in self._arbiter.wrote(reads):
            feed.heard()

    def _read(
        self,
        mixed: Sequence[PlaybackFeed],
    ) -> Tuple[Dict[PlaybackFeed, SourceRead], List[np.ndarray]]:
        """Reads one block from each playback, answering how each read went and the samples each one filled."""
        reads: Dict[PlaybackFeed, SourceRead] = {}
        fills: List[np.ndarray] = []
        for feed in mixed:
            block = silence(self._block_frames)
            try:
                frames = feed.read_into(block, output_rate=self._output_rate)
            except Exception as exception:  # pylint: disable=broad-exception-caught
                logger.error_with_traceback(exception, "A playback's source failed")
                reads[feed] = SourceRead.failed(exception)
                continue

            reads[feed] = SourceRead.filled() if frames == self._block_frames else SourceRead.last()
            fills.append(block[:frames])

        return reads, fills

    def _drain(self) -> None:
        """Plays out what the device holds and closes the stream, which fails a tail the device cuts short."""
        stream = self._require_stream()
        self._stream = None
        try:
            try:
                stream.drain()
            finally:
                stream.close()
        except OSError as exception:
            failure = PlaybackError(f"Failed to close audio stream: {exception}")
            logger.error_with_traceback(failure, "The audio stream failed to play its tail out")
            self._arbiter.closed(failure)
            return

        self._arbiter.closed(None)

    def _abort(self) -> None:
        """Closes the stream at once, cutting what the device holds; a failure to close is logged alone."""
        stream = self._require_stream()
        self._stream = None
        try:
            stream.close()
        except OSError as exception:
            logger.error_with_traceback(exception, "The audio stream failed to close")

        self._arbiter.closed(None)

    def _reconfigure(self) -> None:
        """Takes the settings asked for, renewing the backend first where a refresh asked for it."""
        if not self._arbiter.renewing():
            self._arbiter.reconfigured(None)
            return

        catalog = self._renewed()
        for listener in self._arbiter.reconfigured(catalog):
            self._post(partial(listener, catalog))

    def _renewed(self) -> DeviceCatalog:
        """Renews the backend, answering an empty catalog where the new instance fails to start."""
        try:
            return self._backend.renew()
        except OSError as exception:
            logger.error_with_traceback(exception, "The audio backend failed to restart")
            return DeviceCatalog(devices={}, default_index=None)

    def _require_stream(self) -> OutputStreamProtocol:
        if self._stream is None:
            raise RuntimeError("The writer was asked to use a stream it never opened")

        return self._stream
