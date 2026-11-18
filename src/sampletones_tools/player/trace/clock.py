from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Final

from sampletones_player.rom.clock import ClockDigits, ProgramClock
from sampletones_player.specification.binary import BYTE_VALUES
from sampletones_player.specification.clock import FIXED_POINT_BITS, FIXED_POINT_SCALE
from sampletones_player.specification.program import (
    DIGIT_BASE,
    LONGEST_SHOWN_SECONDS,
    NO_LOOP_FRAMES,
    PROGRESS_SIZE,
    SECOND_STEP,
    SECONDS_PER_MINUTE,
)

BITS_PER_BYTE: Final[int] = 8
PROGRESS_SCALE: Final[int] = 1 << (BITS_PER_BYTE * PROGRESS_SIZE)
COUNTED_SECONDS: Final[int] = LONGEST_SHOWN_SECONDS + 1
SHIMMER_BIT: Final[int] = 0x02
NO_FRAMES: Final[int] = 0


@dataclass(frozen=True)
class CartridgeClock:
    """The clock, the progress bar and the frame count as the cartridge's shell keeps them.

    The shell moves its clock on once for every frame the song plays, with the same byte-wide
    arithmetic the console runs: a 16-bit part of a second whose carry turns the digits, a 24-bit
    progress accumulator whose top byte is the pixels filled, and a frame count running down to
    the song's end. There a song that repeats takes up the figures its loop starts from, and one
    that ends holds them. Stepping this model frame by frame states where the screen stands after
    any number of played frames.

    Attributes:
        program: The figures the exporter writes into the cartridge for the song.
        remaining: The frames left before the song ends or comes round, zero once it has ended.
        seconds: The whole seconds the clock shows, which roll over past the longest it shows.
        second_fraction: The part of a second counted past them, in 1/65536ths.
        progress: The progress bar's fill, in 1/65536ths of a pixel.
        played_frames: The frames played before the song ended, counted in one byte.
    """

    program: ProgramClock
    remaining: int
    seconds: int
    second_fraction: int
    progress: int
    played_frames: int

    @classmethod
    def started(cls, program: ProgramClock) -> CartridgeClock:
        """The clock as the shell starts a song: everything at zero and the whole song to count down."""
        return cls(
            program=program,
            remaining=program.total_frames,
            seconds=0,
            second_fraction=0,
            progress=0,
            played_frames=NO_FRAMES,
        )

    @classmethod
    def after(cls, program: ProgramClock, frames: int) -> CartridgeClock:
        """The clock once ``frames`` frames have played from the start of the song.

        Raises:
            ValueError: If ``frames`` is negative.
        """
        if frames < NO_FRAMES:
            raise ValueError(f"frames must be at least {NO_FRAMES}, got {frames}")

        clock = cls.started(program)
        for _ in range(frames):
            clock = clock.advanced()

        return clock

    @property
    def ended(self) -> bool:
        """Whether a song without a loop has run out of frames, which holds the clock where it stands."""
        return self.remaining == NO_FRAMES

    @property
    def progress_pixels(self) -> int:
        """The pixels of the progress bar filled: the top byte of its accumulator."""
        return self.progress >> FIXED_POINT_BITS

    @property
    def shimmer(self) -> bool:
        """Which of its two arrangements the noise shape stands in, turning every two played frames."""
        return bool(self.played_frames & SHIMMER_BIT)

    def advanced(self) -> CartridgeClock:
        """The clock one played frame on, the song's loop or its end taken where the count runs out."""
        if self.ended:
            return self

        fraction = self.second_fraction + SECOND_STEP
        seconds = self.seconds + fraction // FIXED_POINT_SCALE
        counted = replace(
            self,
            remaining=self.remaining - 1,
            seconds=seconds % COUNTED_SECONDS,
            second_fraction=fraction % FIXED_POINT_SCALE,
            progress=(self.progress + self.program.progress_step) % PROGRESS_SCALE,
            played_frames=(self.played_frames + 1) % BYTE_VALUES,
        )
        if counted.remaining != NO_FRAMES or self.program.loop_frames == NO_LOOP_FRAMES:
            return counted

        return self._come_round(counted)

    @classmethod
    def _come_round(cls, clock: CartridgeClock) -> CartridgeClock:
        """The clock taken back to where the song's loop begins, with the loop's frames to count down."""
        program = clock.program
        return replace(
            clock,
            remaining=program.loop_frames,
            seconds=cls.digit_seconds(program.loop_time),
            second_fraction=program.loop_second,
            progress=program.loop_progress,
        )

    @staticmethod
    def digit_seconds(digits: ClockDigits) -> int:
        """The seconds four clock digits show, minutes then seconds."""
        minute_tens, minute_ones, second_tens, second_ones = digits
        minutes = minute_tens * DIGIT_BASE + minute_ones
        return minutes * SECONDS_PER_MINUTE + second_tens * DIGIT_BASE + second_ones
