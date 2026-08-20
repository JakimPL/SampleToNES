from pydantic import BaseModel, ConfigDict

from sampletones_shared.application import SAMPLETONES_COPYRIGHT


class NSFInformation(BaseModel):
    """The three text fields an NSF header carries, shown by the players that read them.

    Each field reaches the file as a fixed 32-byte string, so text longer than the field holds
    is written as much of itself as fits.

    Attributes:
        title: Name the song is listed under.
        artist: Who the song is credited to.
        copyright: Who holds the rights to it.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    title: str
    artist: str
    copyright: str = SAMPLETONES_COPYRIGHT
