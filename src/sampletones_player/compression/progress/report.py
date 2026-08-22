from dataclasses import dataclass
from typing import Callable, Final


@dataclass(frozen=True)
class CodecProgress:
    """What an encoding run holds at the moment it looks up from its work.

    Attributes:
        phrases: The entries the dictionary has gathered.
        size: The bytes the dictionary and the eight token streams take together, as of the last
            reading of the whole song; a run that has yet to read one reports nothing laid down.
    """

    phrases: int
    size: int


CodecReporter = Callable[[CodecProgress], bool]


def _carry_on(progress: CodecProgress) -> bool:  # pylint: disable=unused-argument
    """Answers that the run goes on, which is what a caller watching nothing asks of it."""
    return True


SILENT_REPORTER: Final[CodecReporter] = _carry_on
