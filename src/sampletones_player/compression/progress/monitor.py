from typing import Final

from sampletones_player.compression.progress.report import CodecProgress, CodecReporter
from sampletones_shared.exceptions import OperationCancelled

NOTHING_FOUND: Final[int] = 0
NOTHING_LAID_DOWN: Final[int] = 0


class CodecMonitor:
    """Carries an encoding run's reckoning of itself to whoever asked for the run.

    Compressing a song of minutes takes seconds, and how many is decided by the song rather than
    by anything the caller can work out beforehand, so the run looks up at the points where it
    has something to say: after each plane it reads, after each phrase the search earns, and
    after each round the table settles through. The monitor keeps what the run last reached, so a
    stretch that has yet to reach a new figure still reports a true one and still asks whether the
    answer is wanted.
    """

    def __init__(self, report: CodecReporter) -> None:
        self._report = report
        self._progress = CodecProgress(phrases=NOTHING_FOUND, size=NOTHING_LAID_DOWN)

    @property
    def progress(self) -> CodecProgress:
        """What the run last reached."""
        return self._progress

    def reached(self, phrases: int, size: int) -> None:
        """Records a reading of the whole song and offers it onward.

        Args:
            phrases: The entries the dictionary now holds.
            size: The bytes the dictionary and the eight streams now take together.

        Raises:
            OperationCancelled: If the run is no longer wanted.
        """
        self._progress = CodecProgress(phrases=phrases, size=size)
        self.poll()

    def poll(self) -> None:
        """Offers what the run last reached, which is how a long stretch answers a withdrawal.

        Raises:
            OperationCancelled: If the run is no longer wanted.
        """
        if not self._report(self._progress):
            raise OperationCancelled(
                f"the encoding was withdrawn holding {self._progress.phrases} phrases "
                f"and {self._progress.size} bytes"
            )
