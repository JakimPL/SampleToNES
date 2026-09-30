from enum import Enum, auto


class SaveOutcome(Enum):
    """What a save the reader asked for came to, which says where a save prompt goes next.

    A save prompt runs its save once it has left the screen, so the outcome decides what follows:
    a document on disk goes on to what the prompt was guarding, a save the reader called off asks
    the question again, and a failed save leaves its error on screen by itself.
    """

    WRITTEN = auto()
    CALLED_OFF = auto()
    FAILED = auto()
