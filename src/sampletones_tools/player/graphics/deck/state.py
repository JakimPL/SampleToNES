from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict, Field

from sampletones_player.compression.pitch import PITCH_COUNT

MAX_LEVEL: Final[int] = 15
DUTY_COUNT: Final[int] = 4
NOISE_PERIOD_COUNT: Final[int] = 16
LAST_PITCH: Final[int] = PITCH_COUNT - 1


class Transport(StrEnum):
    """Whether the song plays, waits or has ended, each named by the glyph that shows it."""

    PLAYING = "play"
    PAUSED = "pause"
    STOPPED = "stop"


class PulseState(BaseModel):
    """What a pulse channel sounds on one frame.

    Attributes:
        duty: Which of the four duty cycles the channel plays, narrowest first.
        level: The channel's volume, where zero rests.
        pitch: The pitch, as the index the song's pitch table is read by.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    duty: int = Field(ge=0, lt=DUTY_COUNT)
    level: int = Field(ge=0, le=MAX_LEVEL)
    pitch: int = Field(ge=0, le=LAST_PITCH)


class TriangleState(BaseModel):
    """What the triangle channel sounds on one frame.

    Attributes:
        sounding: Whether the channel plays, since it has one level alone.
        pitch: The pitch, as the index the song's pitch table is read by.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    sounding: bool
    pitch: int = Field(ge=0, le=LAST_PITCH)


class NoiseState(BaseModel):
    """What the noise channel sounds on one frame.

    Attributes:
        level: The channel's volume, where zero rests.
        period: The period the noise register holds, the longest sounding lowest.
        short: Whether the channel plays its short, pitched sequence.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    level: int = Field(ge=0, le=MAX_LEVEL)
    period: int = Field(ge=0, lt=NOISE_PERIOD_COUNT)
    short: bool


class DeckState(BaseModel):
    """Everything the player screen shows of a song on one frame.

    Attributes:
        title: The program's title line.
        artist: The program's artist line.
        copyright: The program's copyright line.
        pulse1: What the first pulse channel sounds.
        pulse2: What the second pulse channel sounds.
        triangle: What the triangle channel sounds.
        noise: What the noise channel sounds.
        played_seconds: The whole seconds played so far.
        total_seconds: The song's whole length in seconds.
        progress: How many pixels of the progress bar are filled.
        transport: Whether the song plays, waits or has ended.
        shimmer: Which of its two arrangements the noise shape stands in.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    title: str
    artist: str
    copyright: str
    pulse1: PulseState
    pulse2: PulseState
    triangle: TriangleState
    noise: NoiseState
    played_seconds: int = Field(ge=0)
    total_seconds: int = Field(ge=0)
    progress: int = Field(ge=0)
    transport: Transport
    shimmer: bool
