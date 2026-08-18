from pathlib import Path
from typing import BinaryIO, Final, Iterator, Optional

import numpy as np

from sampletones_shared.exceptions import AudioWriteError

NO_PEAK: Final[float] = 0.0


class ScratchAudio:
    """A render's samples spilled to disk beside its destination while their peak is discovered.

    Scaling a render to its peak needs the whole render before any of it can be written, and a
    song is longer than a buffer worth holding in memory. Raw float32 samples are what a private
    intermediate needs: the file is written once, read back once in blocks, and removed, so a
    container would only describe what the writer already knows.

    Attributes:
        path: Where the samples are spilled.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self._handle: Optional[BinaryIO] = None
        self._peak: float = NO_PEAK
        self._samples: int = 0

    @property
    def samples(self) -> int:
        """How many samples have been spilled."""
        return self._samples

    @property
    def peak(self) -> float:
        """The loudest sample spilled so far, as an absolute amplitude."""
        return self._peak

    def start(self) -> None:
        """Opens the spill file, replacing anything a previous run left at the path."""
        self._handle = self.path.open("wb")

    def write(self, chunk: np.ndarray) -> None:
        """Appends one chunk, keeping the loudest sample seen across the whole spill.

        Args:
            chunk: Float samples to spill.

        Raises:
            AudioWriteError: If the spill file is not open.
        """
        if self._handle is None:
            raise AudioWriteError(f"No spill file open at '{self.path}'; write between start and seal")

        chunk.astype(np.float32, copy=False).tofile(self._handle)
        self._peak = max(self._peak, float(np.max(np.abs(chunk), initial=NO_PEAK)))
        self._samples += len(chunk)

    def seal(self) -> None:
        """Closes the spill file, leaving what was written ready to read back."""
        if self._handle is None:
            return

        self._handle.close()
        self._handle = None

    def blocks(self, size: int) -> Iterator[np.ndarray]:
        """Reads the spilled samples back in order, in blocks of at most ``size`` samples.

        Args:
            size: The samples one block holds at most; the last block holds what remains.

        Yields:
            np.ndarray: One block of the spilled float samples.
        """
        with self.path.open("rb") as handle:
            while True:
                block = np.fromfile(handle, dtype=np.float32, count=size)
                if not block.size:
                    return

                yield block

    def remove(self) -> None:
        """Deletes the spill file, whether or not it was read back."""
        self.path.unlink(missing_ok=True)
