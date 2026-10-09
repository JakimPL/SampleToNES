from typing import Final

import pytest

from sampletones_player.compression.pitch import PitchTable
from sampletones_player.registers.streams import ChannelStreams
from sampletones_shared.music import Tuning
from tests.suite.player import (
    PLAYER_FULL_VOLUME,
    PLAYER_SILENT_VOLUME,
    noise_tick,
    player_streams,
    pulse_tick,
    triangle_tick,
)

TUNING: Final[Tuning] = Tuning()
PITCHES: Final[PitchTable] = PitchTable.from_tuning(TUNING)
LOW_INDEX: Final[int] = 36
HIGH_INDEX: Final[int] = 48
NOISE_PERIOD: Final[int] = 0x0A
SOUNDING_TICKS: Final[int] = 3


@pytest.fixture
def pitches() -> PitchTable:
    """The timer each pitch sounds at, at the tuning the fixture's streams were written under."""
    return PITCHES


@pytest.fixture
def sounding_streams() -> ChannelStreams:
    """Four channels sounding at once, the pulse channel walking and the rest holding still."""
    return player_streams(
        pulse1=(
            pulse_tick(PLAYER_FULL_VOLUME, 0, PITCHES.timers[LOW_INDEX]),
            pulse_tick(PLAYER_FULL_VOLUME, 1, PITCHES.timers[HIGH_INDEX]),
            pulse_tick(PLAYER_SILENT_VOLUME, 1, PITCHES.timers[HIGH_INDEX]),
        ),
        pulse2=(pulse_tick(PLAYER_SILENT_VOLUME, 0, PITCHES.timers[LOW_INDEX]),),
        triangle=(triangle_tick(True, PITCHES.timers[LOW_INDEX]),),
        noise=(noise_tick(PLAYER_FULL_VOLUME, 0, NOISE_PERIOD),),
    )
