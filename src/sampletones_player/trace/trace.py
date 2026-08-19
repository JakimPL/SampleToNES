from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Final, List, Tuple

from sampletones_core.constants.enums import GeneratorName
from sampletones_player.song import Song
from sampletones_player.specification.channels import CHANNEL_REGISTER_ADDRESSES
from sampletones_player.specification.registers import (
    APU_FRAME_COUNTER,
    APU_STATUS,
    CHANNELS_ENABLED,
    FIRST_CHANNEL_REGISTER,
    FRAME_COUNTER_SEQUENCE,
    LAST_CHANNEL_REGISTER,
    NOISE_LENGTH_COUNTER,
    NOISE_LENGTH_COUNTER_LOAD,
    PULSE1_SWEEP,
    PULSE2_SWEEP,
    REGISTERS_WRITTEN_ON_CHANGE,
    SILENCED_REGISTER,
    SWEEP_DISABLED,
)
from sampletones_player.trace.write import RegisterWrite

FIRST_TICK: Final[int] = 0


@dataclass(frozen=True)
class RegisterTrace:
    """Every APU register write a run of the driver makes, grouped by the call that makes it.

    This is the contract the assembly is written against: initialisation clears the channels,
    enables them and sounds the song's first tick, and each play call afterwards either advances
    the streams and writes the tick it lands on, or leaves the console alone. The three registers
    that reset a running channel are written only where their value changes, which is what keeps
    a pulse waveform's phase running across a rest the way a rendered channel does.

    A channel sounds only while its length counter stands above zero, and the counter loads from a
    write to the register carrying the length index once the channel is enabled. Initialisation
    therefore reaches those registers after :data:`APU_STATUS`: the noise channel's directly, and
    the three that carry a timer through the first tick's high byte. Halting every counter is what
    holds them there for the rest of the song.

    Attributes:
        initialisation: The writes the init routine makes, leaving the console on the song's
            first tick.
        play_calls: The writes each play call makes, one entry per call, and an empty one for a
            call the streams hold their tick through.
    """

    initialisation: Tuple[RegisterWrite, ...]
    play_calls: Tuple[Tuple[RegisterWrite, ...], ...]

    @staticmethod
    def _tick_writes(
        song: Song,
        tick: int,
        shadows: Dict[int, int],
    ) -> Tuple[RegisterWrite, ...]:
        writes: List[RegisterWrite] = []
        for channel, registers in zip(GeneratorName.items(), song.streams.at(tick)):
            for address, value in zip(CHANNEL_REGISTER_ADDRESSES[channel], registers.values):
                if address in REGISTERS_WRITTEN_ON_CHANGE:
                    if shadows.get(address) == value:
                        continue

                    shadows[address] = value

                writes.append(RegisterWrite(address, value))

        return tuple(writes)

    @classmethod
    def _initialisation_writes(cls, song: Song, shadows: Dict[int, int]) -> Tuple[RegisterWrite, ...]:
        writes = [
            RegisterWrite(address, SILENCED_REGISTER)
            for address in range(FIRST_CHANNEL_REGISTER, LAST_CHANNEL_REGISTER + 1)
        ]
        writes.append(RegisterWrite(APU_STATUS, CHANNELS_ENABLED))
        writes.append(RegisterWrite(APU_FRAME_COUNTER, FRAME_COUNTER_SEQUENCE))
        writes.append(RegisterWrite(PULSE1_SWEEP, SWEEP_DISABLED))
        writes.append(RegisterWrite(PULSE2_SWEEP, SWEEP_DISABLED))
        writes.append(RegisterWrite(NOISE_LENGTH_COUNTER, NOISE_LENGTH_COUNTER_LOAD))
        writes.extend(cls._tick_writes(song, FIRST_TICK, shadows))
        return tuple(writes)

    @classmethod
    def from_song(cls, song: Song, play_calls: int) -> RegisterTrace:
        """States every APU write a correct driver makes over a run of play calls.

        Args:
            song: The streams, the clock and the loop point the driver plays.
            play_calls: How many play calls the run covers, at least 0.

        Returns:
            RegisterTrace: The initialisation writes and the writes of every call in the run.

        Raises:
            ValueError: If ``play_calls`` is negative.
        """
        if play_calls < 0:
            raise ValueError(f"play_calls must be at least 0, got {play_calls}")

        shadows: Dict[int, int] = {}
        initialisation = cls._initialisation_writes(song, shadows)

        calls: List[Tuple[RegisterWrite, ...]] = []
        for play_call in range(play_calls):
            tick = song.tick_at(play_call)
            if tick is None or song.schedule.advance_at(play_call) == 0:
                calls.append(())
                continue

            calls.append(cls._tick_writes(song, tick, shadows))

        return cls(
            initialisation=initialisation,
            play_calls=tuple(calls),
        )
