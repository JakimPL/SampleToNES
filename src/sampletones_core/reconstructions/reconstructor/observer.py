from typing import Final, Protocol

from sampletones_core.reconstructions.reconstructor.decoder.base import Alternatives, Streams


class ReconstructionObserver(Protocol):
    """Hears what a reconstruction decided at each stage, so a measurement can read the search itself.

    A run hands its observer the alternatives the assignment offered, every channel's columns and
    every stem's pools, and the streams the decoder read from them, before refinement bends any note.
    A run assigning its frames again among their neighbors hands over the last pass's alternatives,
    which its streams were decoded from. The observer reads them as they are and leaves the run's
    own state to the run.
    """

    def assigned(self, alternatives: Alternatives) -> None:
        """Hears every channel's columns and every stem's pools, one per frame.

        A column's head is the assignment's pick.
        """

    def decoded(self, streams: Streams) -> None:
        """Hears every channel's decoded stream, one candidate per frame."""


class SilentObserver:
    """An observer that hears every stage and keeps none of it, which is what a conversion runs with."""

    def assigned(self, alternatives: Alternatives) -> None:  # pylint: disable=unused-argument
        return None

    def decoded(self, streams: Streams) -> None:  # pylint: disable=unused-argument
        return None


SILENT_OBSERVER: Final[SilentObserver] = SilentObserver()
