from types import TracebackType
from typing import Optional, Protocol, Self, Type

import numpy as np


class AudioWriter(Protocol):
    """A file open for audio, taking it a chunk at a time for the length of a ``with`` block.

    Writing incrementally is what lets a render of any length report its progress and answer a
    cancel: the caller hands over each chunk as it is produced, and the whole song never has to
    exist in memory at once. Leaving the block finalizes the file, whether the render finished or
    stopped partway, so the destination is a complete file of whatever was written.
    """

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exception_type: Optional[Type[BaseException]],
        exception: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None: ...

    def write(self, chunk: np.ndarray) -> None:
        """Appends one chunk of mono float32 audio to the file.

        Args:
            chunk: The samples to append, in the range [-1, 1].
        """
