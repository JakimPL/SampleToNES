from typing import Final, Tuple

from pydantic import BaseModel

from sampletones_application.view_model.shared.nsf.repeat import NSFRepeat
from sampletones_core.constants.enums import ChannelName
from sampletones_player.compression.scheme import CompressionScheme

FIRST_FRAME: Final[int] = 0
NO_FRAMES: Final[int] = 0


class NSFExportOffer(BaseModel, frozen=True):
    """What one source leaves to choose when it is written as a program.

    A project lays its song out in order frames and seeds the dictionary with its samples, while a
    reconstruction plays its slices once through and seeds nothing, so the choices worth offering
    follow the source: the channels it sounds, the frames a repeat can return to and the schemes
    that write it differently.

    Attributes:
        channels: The channels the source sounds, in channel order.
        frame_count: The order frames the song is laid out in, none for a reconstruction.
        schemes: The compression schemes that write the source differently, lightest first.
    """

    channels: Tuple[ChannelName, ...]
    frame_count: int
    schemes: Tuple[CompressionScheme, ...]

    @property
    def last_frame(self) -> int:
        """The frame a repeat reaches furthest into the song."""
        return max(self.frame_count - 1, FIRST_FRAME)

    @property
    def repeats(self) -> Tuple[NSFRepeat, ...]:
        """The ways the program goes on at its end, a return to a frame offered where frames exist."""
        if self.frame_count > NO_FRAMES:
            return (NSFRepeat.ONCE, NSFRepeat.FROM_START, NSFRepeat.FROM_FRAME)

        return (NSFRepeat.ONCE, NSFRepeat.FROM_START)
