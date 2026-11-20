from enum import StrEnum


class WorkingLevel(StrEnum):
    """The level a variant matches its sounds at.

    ``DEFAULT`` is the level a conversion chooses for itself. ``TRUE`` is the level a sound's file
    holds, which for a sound written as NES frames is the level the channels play its frames at, so a
    reading taken there leaves the working level out of what it measures.
    """

    DEFAULT = "default"
    TRUE = "true"
