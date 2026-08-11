from contextlib import ExitStack
from pathlib import Path
from types import TracebackType
from typing import Callable, Final, Optional, Protocol, Self, Type

import numpy as np

from sampletones_application.services.render.constants import (
    ENCODE_BLOCK_SAMPLES,
    SCRATCH_SUFFIX,
)
from sampletones_application.services.render.scratch import NO_PEAK, ScratchAudio
from sampletones_core.audio.writers import AudioOutputSpec, AudioWriter, open_audio_writer
from sampletones_shared.constants.audio import UNITY_GAIN
from sampletones_shared.exceptions import AudioWriteError

FULL_SCALE: Final[float] = 1.0

EncodeReporter = Callable[[int], bool]


class RenderSink(Protocol):
    """Where a render's rows go on their way to the destination file.

    A sink is entered for the length of one render: rows arrive through ``write`` in the order
    they are synthesised, and ``finish`` completes whatever the sink still owes the destination.
    Leaving the sink closes what it opened and clears what was only ever temporary; ``discard``
    is how a caller that decided against the result removes the file itself.

    Attributes:
        destination: The file the render is written to.
    """

    destination: Path

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exception_type: Optional[Type[BaseException]],
        exception: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None: ...

    def write(self, chunk: np.ndarray) -> None: ...

    def finish(self, report: EncodeReporter, /) -> bool: ...

    def discard(self) -> None: ...


class DirectRenderSink:
    """Writes each row to the destination as it is synthesised.

    One pass over the song, at the level the synthesiser produced: the encoder receives a row as
    soon as it exists, so the file grows with the render and nothing is held between the two.
    """

    def __init__(self, destination: Path, spec: AudioOutputSpec) -> None:
        self.destination = destination
        self._spec = spec
        self._stack = ExitStack()
        self._writer: Optional[AudioWriter] = None

    def __enter__(self) -> Self:
        self._writer = self._stack.enter_context(open_audio_writer(self.destination, self._spec))
        return self

    def __exit__(
        self,
        exception_type: Optional[Type[BaseException]],
        exception: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        self._writer = None
        self._stack.close()

    def write(self, chunk: np.ndarray) -> None:
        """Hands one row to the encoder.

        Args:
            chunk: The row's samples.

        Raises:
            AudioWriteError: If the sink has not been entered.
        """
        if self._writer is None:
            raise AudioWriteError(f"No file open at '{self.destination}'; write within the sink's context")

        self._writer.write(chunk)

    def finish(self, _report: EncodeReporter, /) -> bool:
        """Reports the destination complete, since every row was written as it arrived."""
        return True

    def discard(self) -> None:
        """Deletes the destination, so a render the caller dropped names no file."""
        self.destination.unlink(missing_ok=True)


class NormalizingRenderSink:
    """Spills the render, then writes it at the scale that brings its peak to full.

    The loudest sample is known only once the last row is synthesised, so the rows are spilled
    beside the destination as they arrive and read back in blocks against the peak they turned
    out to hold. The destination is opened for the second pass alone, which is what makes the
    encoder see the finished levels rather than the raw ones.
    """

    def __init__(self, destination: Path, spec: AudioOutputSpec) -> None:
        self.destination = destination
        self._spec = spec
        self._scratch = ScratchAudio(destination.with_name(destination.name + SCRATCH_SUFFIX))

    def __enter__(self) -> Self:
        self._scratch.start()
        return self

    def __exit__(
        self,
        exception_type: Optional[Type[BaseException]],
        exception: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        self._scratch.seal()
        self._scratch.remove()

    def write(self, chunk: np.ndarray) -> None:
        """Spills one row, keeping the peak the render has reached.

        Args:
            chunk: The row's samples.

        Raises:
            AudioWriteError: If the sink has not been entered.
        """
        self._scratch.write(chunk)

    def finish(self, report: EncodeReporter, /) -> bool:
        """Encodes the spilled render at its scale, reporting how far the pass has come.

        Args:
            report: Takes the samples encoded so far and states whether to carry on.

        Returns:
            bool: Whether the destination holds the whole render.
        """
        self._scratch.seal()
        scale = self._scale()
        encoded = 0
        with open_audio_writer(self.destination, self._spec) as writer:
            for block in self._scratch.blocks(ENCODE_BLOCK_SAMPLES):
                writer.write(block * scale)
                encoded += len(block)
                if not report(encoded):
                    return False

        return True

    def discard(self) -> None:
        """Deletes the destination, so a render the caller dropped names no file."""
        self.destination.unlink(missing_ok=True)

    def _scale(self) -> float:
        """The factor bringing the spilled render's peak to full scale.

        A render that stayed silent has no peak to reach for, so it is written as it stands.
        """
        if self._scratch.peak <= NO_PEAK:
            return UNITY_GAIN

        return FULL_SCALE / self._scratch.peak


def build_render_sink(
    destination: Path,
    spec: AudioOutputSpec,
    *,
    normalize: bool,
) -> RenderSink:
    """The sink a render writes through, chosen by whether its level is scaled to its peak.

    Args:
        destination: The file the render is written to.
        spec: The format, rate, and quality it is written at.
        normalize: Whether the render is scaled so its loudest sample reaches full scale.

    Returns:
        RenderSink: A sink ready to be entered.
    """
    if normalize:
        return NormalizingRenderSink(destination, spec)

    return DirectRenderSink(destination, spec)
