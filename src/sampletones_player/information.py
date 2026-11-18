from __future__ import annotations

import unicodedata
from typing import Dict, Final, Literal

from pydantic import BaseModel, ConfigDict, Field

from sampletones_shared.application import SAMPLETONES_COPYRIGHT

REPLACING_UNKNOWN_CHARACTERS: Final[str] = "replace"
DROPPING_CUT_CHARACTERS: Final[str] = "ignore"
DECOMPOSITION: Final[Literal["NFKD"]] = "NFKD"
BASE_LETTERS: Final[Dict[str, str]] = {
    "ł": "l",
    "Ł": "L",
    "ø": "o",
    "Ø": "O",
    "đ": "d",
    "Đ": "D",
    "ß": "ss",
    "æ": "ae",
    "Æ": "AE",
    "œ": "oe",
    "Œ": "OE",
}


class TextLine(BaseModel):
    """The room a file gives one line of a program's text, counted in the encoding it is written in.

    A program is listed under three lines of text, and each kind of file holds a line its own
    way. A line states the encoding the text reaches the file in and how many units of that
    encoding fit, so whoever offers the text for editing shows exactly what the file will carry.

    A folded line writes every character as text its encoding holds before it counts or cuts:
    a character the encoding holds stays itself, an accented letter becomes the letters it is
    built on (``ż`` as ``z``), and a letter built on none becomes the one :data:`BASE_LETTERS`
    names (``ł`` as ``l``). A font drawing a handful of glyphs then shows a name as close to its
    spelling as those glyphs reach.

    Attributes:
        encoding: The encoding the text is written in.
        room: The encoded units one line holds.
        folded: Whether each character is written as the nearest text the encoding holds.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    encoding: str
    room: int = Field(..., ge=1)
    folded: bool

    def fit(self, text: str) -> str:
        """The part of ``text`` the line holds.

        The line holds the longest run of whole characters whose encoding fits its room. A
        character the encoding has no code for is held as the mark the encoding replaces it with.

        Args:
            text: The text offered for the line.

        Returns:
            str: ``text`` itself, or as many of its leading characters as the line holds,
            folded where the line folds.
        """
        return self._encoded(text)[: self.room].decode(self.encoding, errors=DROPPING_CUT_CHARACTERS)

    def size(self, text: str) -> int:
        """The units ``text`` takes on the line, folded where the line folds."""
        return len(self._encoded(text))

    def _encoded(self, text: str) -> bytes:
        shown = self._folded(text) if self.folded else text
        return shown.encode(self.encoding, errors=REPLACING_UNKNOWN_CHARACTERS)

    def _folded(self, text: str) -> str:
        return "".join(self._folded_character(character) for character in text)

    def _folded_character(self, character: str) -> str:
        """The text ``character`` is written as: itself, the letters it decomposes into, or its base letter.

        A character with none of the three stays itself, so the encoding writes it as its
        replacement mark.
        """
        if self._holds(character):
            return character

        decomposed = "".join(part for part in unicodedata.normalize(DECOMPOSITION, character) if self._holds(part))
        if decomposed:
            return decomposed

        return BASE_LETTERS.get(character, character)

    def _holds(self, character: str) -> bool:
        try:
            character.encode(self.encoding)
        except UnicodeEncodeError:
            return False

        return True


class ProgramText(BaseModel):
    """The room a file gives each of a program's three lines of text.

    A file may give its lines different room, as a screen setting a line beside its label does,
    so each line states its own.

    Attributes:
        title: The line the song's name is listed on.
        artist: The line the song is credited on.
        copyright: The line stating who holds the rights.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    title: TextLine
    artist: TextLine
    copyright: TextLine


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

    def fitted(self, text: ProgramText) -> ProgramInformation:
        """The text as a file giving its lines the room ``text`` states carries it.

        Args:
            text: The room each line has.

        Returns:
            ProgramInformation: Every line held as the part of itself its own room holds.
        """
        return ProgramInformation(
            title=text.title.fit(self.title),
            artist=text.artist.fit(self.artist),
            copyright=text.copyright.fit(self.copyright),
        )
