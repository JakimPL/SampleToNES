from enum import StrEnum


class VariantLevel(StrEnum):
    """The level a variant matches its sounds at.

    ``DEFAULT`` is the working level a conversion chooses for itself. ``TRUE`` is the level a sound's
    file holds, which takes the place of the working level whole, under every level method. For a
    sound written as NES frames it is the level the channels play its frames at, so a reading taken
    there leaves the working level out of what it measures.
    """

    DEFAULT = "default"
    TRUE = "true"
