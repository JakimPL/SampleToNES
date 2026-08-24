from dataclasses import dataclass
from typing import Callable


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
