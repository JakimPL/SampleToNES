from typing import Final

from pydantic import BaseModel, ConfigDict, field_validator

from sampletones_player.specification.nsf import STRING_TEXT_SIZE
from sampletones_shared.application import SAMPLETONES_COPYRIGHT

TEXT_ENCODING: Final[str] = "utf-8"


def fit_field(text: str) -> str:
    """The part of ``text`` a header string field holds.

    A field is a fixed run of bytes ending in a terminator, so its text is the longest run of
    whole characters whose encoding fits in front of it. What a player lists is what this returns,
    which lets whoever offers the text for editing show exactly what the file will carry.

    Args:
        text: The text offered for the field.

    Returns:
        str: ``text`` itself, or as many of its leading characters as the field holds.
    """
    return text.encode(TEXT_ENCODING)[:STRING_TEXT_SIZE].decode(TEXT_ENCODING, errors="ignore")


class NSFInformation(BaseModel):
    """The three text fields an NSF header carries, shown by the players that read them.

    Each field reaches the file as a fixed 32-byte string ending in a terminator, so every text
    is held as the part of itself the field has room for (:func:`fit_field`).

    Attributes:
        title: Name the song is listed under.
        artist: Who the song is credited to.
        copyright: Who holds the rights to it.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    title: str
    artist: str
    copyright: str = SAMPLETONES_COPYRIGHT

    @field_validator("title", "artist", "copyright")
    @classmethod
    def _fit_each_field(cls, text: str) -> str:
        return fit_field(text)
