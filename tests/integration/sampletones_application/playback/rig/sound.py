from enum import Enum
from typing import Final, Tuple


class Sound(Enum):
    """Each sound the application starts, named by the owner a reader starts it through."""

    RECONSTRUCTION = "reconstruction"
    INSTRUCTION = "instruction"
    SONG = "song"
    VOICE = "voice"
    FILE = "file"
    KEYS = "keys"


SOURCES: Final[Tuple[Sound, ...]] = (Sound.RECONSTRUCTION, Sound.INSTRUCTION, Sound.SONG)
BUFFERS: Final[Tuple[Sound, ...]] = (Sound.RECONSTRUCTION, Sound.INSTRUCTION)
PREVIEWS: Final[Tuple[Sound, ...]] = (Sound.VOICE, Sound.FILE, Sound.KEYS)
