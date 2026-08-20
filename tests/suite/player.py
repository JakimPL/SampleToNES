import os
from pathlib import Path
from typing import Dict, Final, List, Optional, Sequence

import numpy as np

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_PITCH, MIN_PITCH
from sampletones_core.exporters import Features
from sampletones_core.exports.request import InstrumentExport, SampleExport
from sampletones_core.instructions import InstructionUnion, PulseInstruction
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.timers.arithmetic import frequency_to_timer
from sampletones_player.clock.schedule import PlaySchedule
from sampletones_player.registers.noise import NoiseRegisters
from sampletones_player.registers.pulse import PulseRegisters
from sampletones_player.registers.streams import ChannelStreams
from sampletones_player.registers.triangle import TriangleRegisters
from sampletones_player.song import Song
from sampletones_player.specification.registers import (
    DUTY_CYCLE_SHIFT,
    MAX_REGISTER_VALUE,
    NOISE_MODE_SHIFT,
    SUSTAINED_LEVEL,
    TIMER_HIGH_SHIFT,
    TRIANGLE_COUNTER_CONTROL,
    TRIANGLE_SILENT_RELOAD,
    TRIANGLE_SOUNDING_RELOAD,
)
from sampletones_shared.music import Tuning
from sampletones_shared.utils.frequencies import pitch_to_frequency

PLAYER_REFERENCE_TIMER: Final[int] = 0x154
PLAYER_OCTAVE_UP_TIMER: Final[int] = PLAYER_REFERENCE_TIMER // 2
PLAYER_REFERENCE_PERIOD: Final[int] = 0x0A
PLAYER_FULL_VOLUME: Final[int] = 15
PLAYER_SILENT_VOLUME: Final[int] = 0


def pulse_tick(
    volume: int,
    duty_cycle: int,
    timer: int,
) -> PulseRegisters:
    """A pulse channel's registers for one tick, spelled the way the encoder spells them."""
    return PulseRegisters(
        control=(duty_cycle << DUTY_CYCLE_SHIFT) | SUSTAINED_LEVEL | volume,
        timer_low=timer & MAX_REGISTER_VALUE,
        timer_high=timer >> TIMER_HIGH_SHIFT,
    )


def triangle_tick(sounding: bool, timer: int) -> TriangleRegisters:
    """A triangle channel's registers for one tick, spelled the way the encoder spells them."""
    reload_value = TRIANGLE_SOUNDING_RELOAD if sounding else TRIANGLE_SILENT_RELOAD
    return TriangleRegisters(
        linear_counter=TRIANGLE_COUNTER_CONTROL | reload_value,
        timer_low=timer & MAX_REGISTER_VALUE,
        timer_high=timer >> TIMER_HIGH_SHIFT,
    )


def noise_tick(
    volume: int,
    mode: int,
    register_period: int,
) -> NoiseRegisters:
    """A noise channel's registers for one tick, its period counted the way ``$400E`` counts it."""
    return NoiseRegisters(
        control=SUSTAINED_LEVEL | volume,
        period=(mode << NOISE_MODE_SHIFT) | register_period,
    )


def player_streams(
    pulse1: Sequence[PulseRegisters],
    pulse2: Sequence[PulseRegisters],
    triangle: Sequence[TriangleRegisters],
    noise: Sequence[NoiseRegisters],
) -> ChannelStreams:
    return ChannelStreams(
        pulse1=tuple(pulse1),
        pulse2=tuple(pulse2),
        triangle=tuple(triangle),
        noise=tuple(noise),
    )


def resting_streams(pulse1: Sequence[PulseRegisters]) -> ChannelStreams:
    """Streams where one pulse channel carries the song and the other three rest on a single tick."""
    return player_streams(
        pulse1=pulse1,
        pulse2=(pulse_tick(PLAYER_SILENT_VOLUME, 0, PLAYER_REFERENCE_TIMER),),
        triangle=(triangle_tick(False, PLAYER_REFERENCE_TIMER),),
        noise=(noise_tick(PLAYER_SILENT_VOLUME, 0, PLAYER_REFERENCE_PERIOD),),
    )


def player_song(
    streams: ChannelStreams,
    nes_frequency: int,
    loop_tick: Optional[int],
) -> Song:
    return Song(
        streams=streams,
        schedule=PlaySchedule.from_parameters(nes_frequency),
        loop_tick=loop_tick,
    )


PLAYER_TIMER_TABLE: Final[Dict[int, int]] = {
    pitch: frequency_to_timer(pitch_to_frequency(pitch)) for pitch in range(MIN_PITCH, MAX_PITCH + 1)
}
PLAYER_REFERENCE_PITCH: Final[int] = 69
PLAYER_PULSE_TIMER_MUTE_FLOOR: Final[int] = 8


def sounding_pulse(
    pitch: int,
    volume: int,
    duty_cycle: int,
) -> PulseInstruction:
    return PulseInstruction(
        on=True,
        pitch=pitch,
        volume=volume,
        duty_cycle=duty_cycle,
    )


def silent_pulse() -> PulseInstruction:
    return PulseInstruction.null_instruction()


PLAYER_APPROXIMATION_SAMPLES: Final[int] = 64


def player_reconstruction(
    instructions: Dict[ChannelName, List[InstructionUnion]],
    nes_frequency: int,
) -> Reconstruction:
    """A reconstruction carrying the given channel streams, built at ``nes_frequency``.

    The audio itself is silent, since what a player test reads off a reconstruction is the
    instructions its channels carry and the rate they advance at.
    """
    return Reconstruction.create(
        approximation=np.zeros(PLAYER_APPROXIMATION_SAMPLES, dtype=np.float32),
        approximations={},
        instructions=instructions,
        config=Config().with_library(nes_frequency=nes_frequency),
        coefficient=1.0,
        audio_filepath=Path(os.devnull),
    )


PLAYER_TUNING: Final[Tuning] = Tuning()


def player_features(
    frames: int,
    pitch: int,
    *,
    duty_cycle: bool,
) -> Features:
    """Envelopes sounding one pitch at full volume for ``frames`` ticks."""
    return Features(
        initial_pitch=pitch,
        volume=np.full(frames, PLAYER_FULL_VOLUME, dtype=int),
        arpeggio=np.zeros(frames, dtype=int),
        pitch=None,
        hi_pitch=None,
        duty_cycle=np.zeros(frames, dtype=int) if duty_cycle else None,
    )


def player_instrument(
    name: str,
    channel: ChannelName,
    features: Features,
    *,
    nes_frequency: int,
    loop: bool,
    tuning: Tuning = PLAYER_TUNING,
) -> InstrumentExport:
    """One channel slice of an export request."""
    return InstrumentExport(
        name=name,
        channel=channel,
        features=features,
        loop=loop,
        nes_frequency=nes_frequency,
        tuning=tuning,
    )


def player_sample(
    name: str,
    instruments: Sequence[InstrumentExport],
    *,
    nes_frequency: int,
    tuning: Tuning = PLAYER_TUNING,
) -> SampleExport:
    """Every channel slice of one reconstruction, as an export request carries them."""
    return SampleExport(
        name=name,
        instruments=tuple(instruments),
        nes_frequency=nes_frequency,
        tuning=tuning,
    )
