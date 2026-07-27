from enum import Enum


class FieldKind(Enum):
    """What a focused widget does with a key press, which decides the keys it keeps for itself.

    ``TEXT_ENTRY`` inserts typed characters (text and number inputs); ``CHOICE`` navigates a list
    of options (an open combo); ``NONE`` is any other focus, which yields every key.
    """

    NONE = "none"
    TEXT_ENTRY = "text_entry"
    CHOICE = "choice"
