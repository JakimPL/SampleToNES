from typing import List, Protocol, Tuple

from pydantic import BaseModel, ConfigDict, Field

from sampletones_core.timing.bounds import MAX_TICKS_PER_ROW
from sampletones_player.specification.registers import (
    APU_FRAME_COUNTER,
    DMC_DIRECT_LOAD,
    FIRST_CHANNEL_REGISTER,
    MAX_REGISTER_VALUE,
)
from sampletones_tools.player.trace.write import RegisterWrite
from sampletones_tools.tracker_playback.targets.famitracker.errors import FamiTrackerError
from sampletones_tools.tracker_playback.targets.famitracker.markers import row_marker
from sampletones_tools.tracker_playback.trace.decode import song_trace
from sampletones_tools.tracker_playback.trace.registers import ChipRegisters
from sampletones_tools.tracker_playback.trace.sound import SongTrace, TickPosition


class PlayCalls(Protocol):
    """What runs an NSF one routine at a time and answers with the APU writes each routine made."""

    def initialize(self) -> Tuple[RegisterWrite, ...]:
        """Runs the init routine."""

    def play(self) -> Tuple[RegisterWrite, ...]:
        """Runs one play call."""


class DriverWrite(BaseModel):
    """One write FamiTracker's NSF driver makes to the APU.

    Attributes:
        address: The register written.
        value: The byte written.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    address: int = Field(..., ge=FIRST_CHANNEL_REGISTER, le=APU_FRAME_COUNTER)
    value: int = Field(..., ge=0, le=MAX_REGISTER_VALUE)


class DriverTick(BaseModel):
    """Every write FamiTracker's NSF driver made on one tick, and where in the song the tick falls.

    The first tick also carries the writes of any play call before the song's first row.

    Attributes:
        frame: The order frame being played.
        row: The row of that frame's patterns.
        writes: The writes, in the order the driver made them.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    frame: int
    row: int
    writes: Tuple[DriverWrite, ...]


class DriverTrace(BaseModel):
    """One pass through a song as FamiTracker's NSF driver plays it, tick by tick.

    Attributes:
        initialization: The writes the init routine made.
        ticks: Every tick of the pass.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    initialization: Tuple[DriverWrite, ...]
    ticks: Tuple[DriverTick, ...]

    def song_trace(self) -> SongTrace:
        """What every channel sounds on every tick, read out of the registers the driver wrote.

        Returns:
            SongTrace: The pass.
        """
        registers = ChipRegisters.power_up().written(_register_writes(self.initialization))
        per_tick: List[ChipRegisters] = []
        for tick in self.ticks:
            registers = registers.written(_register_writes(tick.writes))
            per_tick.append(registers)

        return song_trace(
            tuple(TickPosition(frame=tick.frame, row=tick.row) for tick in self.ticks),
            per_tick,
        )


def recorded_trace(
    calls: PlayCalls,
    *,
    frames: int,
    rows: int,
) -> DriverTrace:
    """Plays one pass through a song whose rows carry markers, and splits the play calls into its ticks.

    A play call writing a marker starts a row, and every call up to the next marker plays that row.
    The pass ends at the marker after the song's last row, where the order comes back round. No
    project holds a row longer than ``MAX_TICKS_PER_ROW`` ticks, so a row lasting longer is a driver
    that stopped moving through the song.

    Args:
        calls: The NSF's routines.
        frames: The order frames the song plays.
        rows: The rows each pattern holds.

    Returns:
        DriverTrace: The pass.

    Raises:
        FamiTrackerError: If a row's marker carries a level other than its place in the song, or a row
            lasts longer than ``MAX_TICKS_PER_ROW`` calls.
    """
    initialization = _driver_writes(calls.initialize())
    song_rows = frames * rows
    row_index = -1
    row_ticks = 0
    pending: List[DriverWrite] = []
    ticks: List[DriverTick] = []
    while True:
        writes = calls.play()
        markers = [write.value for write in writes if write.address == DMC_DIRECT_LOAD]
        if markers:
            row_index += 1
            row_ticks = 0
            if row_index == song_rows:
                break

            _check_marker(markers[-1], row_index)

        row_ticks += 1
        if row_ticks > MAX_TICKS_PER_ROW:
            raise FamiTrackerError(
                f"FamiTracker's NSF driver held row {row_index} for more than {MAX_TICKS_PER_ROW} ticks"
            )

        pending.extend(_driver_writes(writes))
        if row_index < 0:
            continue

        ticks.append(DriverTick(frame=row_index // rows, row=row_index % rows, writes=tuple(pending)))
        pending = []

    return DriverTrace(initialization=initialization, ticks=tuple(ticks))


def _check_marker(level: int, row_index: int) -> None:
    expected = row_marker(row_index)
    if level != expected:
        raise FamiTrackerError(
            f"FamiTracker's NSF driver marked row {row_index} with {level}, where that row carries {expected}"
        )


def _driver_writes(writes: Tuple[RegisterWrite, ...]) -> Tuple[DriverWrite, ...]:
    return tuple(DriverWrite(address=write.address, value=write.value) for write in writes)


def _register_writes(writes: Tuple[DriverWrite, ...]) -> Tuple[RegisterWrite, ...]:
    return tuple(RegisterWrite(write.address, write.value) for write in writes)
