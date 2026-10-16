from typing import Final, Optional

from pydantic import BaseModel, Field

DEFAULT_VELOCITY_SETS_VOLUME: Final[bool] = True


class MidiConfig(BaseModel):
    """The MIDI keyboard a user reads and how its keys are read.

    The port is kept by its name, which stays the same as devices come and go, so a keyboard unplugged for one
    run is looked for again in the next.
    """

    port: Optional[str] = Field(
        default=None,
        description="The name of the MIDI input read, or none while no keyboard is.",
    )
    velocity_sets_volume: bool = Field(
        default=DEFAULT_VELOCITY_SETS_VOLUME,
        description="Whether how hard a key is struck sets the volume it plays and writes at.",
    )
