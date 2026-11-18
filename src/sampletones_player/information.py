from __future__ import annotations

from typing import Final

from pydantic import BaseModel, ConfigDict, Field

from sampletones_shared.application import SAMPLETONES_COPYRIGHT

REPLACING_UNKNOWN_CHARACTERS: Final[str] = "replace"
DROPPING_CUT_CHARACTERS: Final[str] = "ignore"


class TextLine(BaseModel):
    """The room a file gives one line of a program's text, counted in the encoding it is written in.

    A program is listed under three lines of text, and each kind of file holds a line its own
    way. A line states the encoding the text reaches the file in and how many units of that
    encoding fit, so whoever offers the text for editing shows exactly what the file will carry.

    Attributes:
        encoding: The encoding the text is written in.
        room: The encoded units one line holds.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    encoding: str
    room: int = Field(..., ge=1)

    def fit(self, text: str) -> str:
        """The part of ``text`` the line holds.

        The line holds the longest run of whole characters whose encoding fits its room. A
        character the encoding has no code for is held as the mark the encoding replaces it with.

        Args:
            text: The text offered for the line.

        Returns:
            str: ``text`` itself, or as many of its leading characters as the line holds.
        """
        return self._encoded(text)[: self.room].decode(self.encoding, errors=DROPPING_CUT_CHARACTERS)

    def size(self, text: str) -> int:
        """The units ``text`` takes on the line."""
        return len(self._encoded(text))

    def _encoded(self, text: str) -> bytes:
        return text.encode(self.encoding, errors=REPLACING_UNKNOWN_CHARACTERS)


class ProgramInformation(BaseModel):
    """The three lines of text a program is listed under.

    The text is kept as it was given, and each kind of file carries the part of every line it
    has room for, which :meth:`fitted` answers with.

    Attributes:
        title: Name the song is listed under.
        artist: Who the song is credited to.
        copyright: Who holds the rights to it.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    title: str
    artist: str
    copyright: str = SAMPLETONES_COPYRIGHT

    def fitted(self, line: TextLine) -> ProgramInformation:
        """The text as a file giving each line the room ``line`` states carries it.

        Args:
            line: The room one line has.

        Returns:
            ProgramInformation: Every line held as the part of itself that fits.
        """
        return ProgramInformation(
            title=line.fit(self.title),
            artist=line.fit(self.artist),
            copyright=line.fit(self.copyright),
        )
