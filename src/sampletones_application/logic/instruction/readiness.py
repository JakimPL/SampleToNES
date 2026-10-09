from enum import Enum, auto


class LibraryReadiness(Enum):
    """Where the library a conversion converts against stands while the conversion waits for it."""

    PREPARING = auto()
    READY = auto()
    MISSING = auto()
