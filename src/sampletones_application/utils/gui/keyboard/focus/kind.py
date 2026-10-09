from enum import Enum


class FieldKind(Enum):
    """What a focused widget does with a key press, which decides the keys it keeps for itself.

    ``TEXT_ENTRY`` inserts any typed character (a text input). ``NUMBER_ENTRY`` inserts the
    characters of a number (a number input, a slider or a drag being typed into). ``CHOICE``
    navigates a list of options (an open combo). ``NONE`` is any other focus, which yields every key.
    """

    NONE = "none"
    TEXT_ENTRY = "text_entry"
    NUMBER_ENTRY = "number_entry"
    CHOICE = "choice"

    @property
    def takes_typing(self) -> bool:
        """Whether the field inserts the characters typed into it."""
        return self in (FieldKind.TEXT_ENTRY, FieldKind.NUMBER_ENTRY)
