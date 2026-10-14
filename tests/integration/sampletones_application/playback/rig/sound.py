from enum import Enum
from typing import Final, Tuple


class Sound(Enum):
    """Each sound the application starts, named by the owner a reader starts it through."""

    RECONSTRUCTION = "reconstruction"
    INSTRUCTION = "instruction"
    SONG = "song"
    AUDITION = "audition"
    VOICE = "voice"
    FILE = "file"


SOURCES: Final[Tuple[Sound, ...]] = (Sound.RECONSTRUCTION, Sound.INSTRUCTION, Sound.SONG)
BUFFERS: Final[Tuple[Sound, ...]] = (Sound.RECONSTRUCTION, Sound.INSTRUCTION)
PREVIEWS: Final[Tuple[Sound, ...]] = (Sound.AUDITION, Sound.VOICE, Sound.FILE)
