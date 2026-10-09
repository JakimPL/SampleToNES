from enum import StrEnum
from typing import Dict, Final, List, Tuple

from pydantic import BaseModel, ConfigDict, Field

from sampletones_core.constants.enums import ChannelName
from sampletones_player.specification.registers import (
    APU_FRAME_COUNTER,
    APU_STATUS,
    FIRST_CHANNEL_REGISTER,
    MAX_REGISTER_VALUE,
)
from sampletones_tools.player.trace.write import RegisterWrite
from sampletones_tools.tracker_playback.trace.decode import (
    CHANNEL_STATUS_BITS,
    DMC_STATUS_BIT,
    song_trace,
)
from sampletones_tools.tracker_playback.trace.registers import ChipRegisters
from sampletones_tools.tracker_playback.trace.sound import SongTrace, TickPosition


class EmulatorUnit(StrEnum):
    """The two units Bitphase's emulator splits the APU into, each written through an export of its own.

    `apu` plays the two pulse channels and `dmc` plays the triangle, the noise and the DMC. Each
    keeps its own copy of the status register and reads only its own channels' bits of it.
    """

    APU = "apu"
    DMC = "dmc"


UNIT_STATUS_BITS: Final[Dict[EmulatorUnit, int]] = {
    EmulatorUnit.APU: CHANNEL_STATUS_BITS[ChannelName.PULSE1] | CHANNEL_STATUS_BITS[ChannelName.PULSE2],
    EmulatorUnit.DMC: (
        CHANNEL_STATUS_BITS[ChannelName.TRIANGLE] | CHANNEL_STATUS_BITS[ChannelName.NOISE] | DMC_STATUS_BIT
    ),
}


class UnitWrite(BaseModel):
    """One write Bitphase's engine makes to a unit of its emulated APU.

    Attributes:
        unit: The unit the write reaches.
        address: The register written.
        value: The byte written.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    unit: EmulatorUnit
    address: int = Field(..., ge=FIRST_CHANNEL_REGISTER, le=APU_FRAME_COUNTER)
    value: int = Field(..., ge=0, le=MAX_REGISTER_VALUE)

    def chip_write(self, status: int) -> RegisterWrite:
        """The write as one whole APU takes it, given the status register standing before it.

        A status write reaches the bits of the channels its unit plays and leaves the other unit's
        bits as they stand, which is what the two units enable between them.

        Args:
            status: The status register before the write.

        Returns:
            RegisterWrite: The write the whole chip takes.
        """
        if self.address != APU_STATUS:
            return RegisterWrite(self.address, self.value)

        bits = UNIT_STATUS_BITS[self.unit]
        return RegisterWrite(APU_STATUS, (status & ~bits) | (self.value & bits))


class EngineTick(BaseModel):
    """Every write Bitphase's engine made to the chip since the tick before, and where in the song the tick falls.

    The first tick also carries the writes the engine makes as it resets the chip and before it
    plays.

    Attributes:
        frame: The order position being played.
        row: The row of that position's pattern.
        writes: The writes, in the order the engine made them.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    frame: int
    row: int
    writes: Tuple[UnitWrite, ...]


class EngineTrace(BaseModel):
    """Every tick of one pass through a document, as the trace script writes it."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ticks: Tuple[EngineTick, ...]

    @property
    def positions(self) -> Tuple[TickPosition, ...]:
        """Where each tick falls."""
        return tuple(TickPosition(frame=tick.frame, row=tick.row) for tick in self.ticks)

    def registers(self) -> Tuple[ChipRegisters, ...]:
        """The chip's registers on every tick, each tick's writes laid over what the tick before left.

        Returns:
            Tuple[ChipRegisters, ...]: The registers on each tick, one per tick.
        """
        registers = ChipRegisters.power_up()
        per_tick: List[ChipRegisters] = []
        for tick in self.ticks:
            for write in tick.writes:
                registers = registers.written((write.chip_write(registers.value(APU_STATUS)),))

            per_tick.append(registers)

        return tuple(per_tick)


def read_engine_trace(text: str) -> SongTrace:
    """What a trace script's output says every channel plays, read out of the registers the engine wrote.

    Args:
        text: The JSON the trace script wrote.

    Returns:
        SongTrace: One pass through the song.

    Raises:
        ValidationError: If the text is no trace the script writes.
    """
    trace = EngineTrace.model_validate_json(text)
    return song_trace(trace.positions, trace.registers())
