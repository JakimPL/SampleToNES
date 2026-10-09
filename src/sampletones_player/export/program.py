from __future__ import annotations

from typing import Annotated, Final, FrozenSet, Optional

from pydantic import BaseModel, ConfigDict, Field

from sampletones_core.constants.enums import ALL_CHANNELS, ChannelName
from sampletones_core.exports.request import SampleExport
from sampletones_core.project.project import Project
from sampletones_player.builder import SONG_START, loop_tick_from_instruments
from sampletones_player.compression.scheme import CompressionScheme
from sampletones_player.nsf.information import NSFInformation
from sampletones_shared.application import SAMPLETONES_COPYRIGHT

NO_ARTIST: Final[str] = ""
DEFAULT_SCHEME: Final[CompressionScheme] = CompressionScheme.SEARCH


class NSFProgram(BaseModel):
    """Everything a written program states beyond the song it plays.

    A song reaches the console as the channels it sounds, the tick it returns to once it ends and
    the layers it is compressed with, and the file lists it under three lines of text. Those are
    the choices an export makes, and :meth:`for_project` and :meth:`for_sample` state the ones it
    makes on its own.

    Attributes:
        information: The text the file is listed under.
        channels: The channels the program sounds, every other one resting throughout.
        loop_tick: The tick the song returns to once it ends, or ``None`` where it stops there.
        scheme: The layers of the codec the song is written with.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    information: NSFInformation
    channels: FrozenSet[ChannelName] = Field(min_length=1)
    loop_tick: Optional[Annotated[int, Field(ge=0)]]
    scheme: CompressionScheme

    @classmethod
    def for_project(cls, project: Project) -> NSFProgram:
        """The program a whole composition is written as.

        The file is listed under the project's own title and author, sounds every channel, and
        repeats from its first tick, which is how a piece of music is listened to and what an NSF
        player expects of a song that has reached its end.

        Args:
            project: The composition to write.

        Returns:
            NSFProgram: The program, compressed as hard as the codec reaches.
        """
        return cls(
            information=NSFInformation(
                title=project.info.title,
                artist=project.info.author,
                copyright=SAMPLETONES_COPYRIGHT,
            ),
            channels=ALL_CHANNELS,
            loop_tick=SONG_START,
            scheme=DEFAULT_SCHEME,
        )

    @classmethod
    def for_sample(cls, request: SampleExport) -> NSFProgram:
        """The program a reconstruction's slices are written as.

        The file is listed under the reconstruction's name and credited to nobody, sounds every
        slice the request carries, and repeats where every slice repeats.

        Args:
            request: The slices to write.

        Returns:
            NSFProgram: The program, compressed as hard as the codec reaches.
        """
        return cls(
            information=NSFInformation(
                title=request.name,
                artist=NO_ARTIST,
                copyright=SAMPLETONES_COPYRIGHT,
            ),
            channels=ALL_CHANNELS,
            loop_tick=loop_tick_from_instruments(request.instruments),
            scheme=DEFAULT_SCHEME,
        )
