from dataclasses import dataclass
from typing import Any, Dict, Final, Optional, Tuple

import numpy as np

from sampletones_core.constants.algorithm import RESET_PHASE
from sampletones_core.constants.general import (
    APU_CLOCK,
    MAX_LFSR,
    MAX_LFSR_SHORT,
    MAX_PERIOD,
    NOISE_PERIODS,
)
from sampletones_shared.types.data import Initials

from ..timer import Timer

CYCLE_START: Final[int] = 0
OFF_CYCLE: Final[int] = -1


def cycle_length(short: bool) -> int:
    """The number of steps after which the shift register returns to its starting value."""
    return MAX_LFSR_SHORT if short else MAX_LFSR


def step_lfsr(lfsr: int, short: bool) -> int:
    """Advances the 15-bit shift register one step.

    Feedback is ``bit0 ^ bit1`` in long mode and ``bit0 ^ bit6`` in short mode, shifted into
    bit 14, as the 2A03 noise channel does.

    Args:
        lfsr: The current register value, 1 to ``MAX_LFSR``.
        short: Whether the register runs in its 93-step short mode.

    Returns:
        int: The register after one step.
    """
    feedback = (lfsr & 1) ^ ((lfsr >> (6 if short else 1)) & 1)
    return ((lfsr >> 1) | (feedback << 14)) & MAX_LFSR


def step_lfsr_back(lfsr: int, short: bool) -> int:
    """Rewinds the 15-bit shift register one step, inverting :func:`step_lfsr`.

    Args:
        lfsr: The current register value, 1 to ``MAX_LFSR``.
        short: Whether the register runs in its 93-step short mode.

    Returns:
        int: The register one step earlier.
    """
    partial = (lfsr & 0x3FFF) << 1
    feedback = ((lfsr >> 14) & 1) ^ ((partial >> (6 if short else 1)) & 1)
    return (partial | feedback) & MAX_LFSR


@dataclass(frozen=True)
class LFSRTables:
    """Lookups covering one feedback mode's shift-register cycle.

    Attributes:
        lfsrs: The register values of one full cycle, starting from the seed value 1.
        lfsr_to_index: Position within ``lfsrs`` of every register value on the cycle, and
            ``OFF_CYCLE`` for values this mode's feedback places on a different cycle.
        bit_prefix: Running count of set output bits over the cycle, repeated far enough that
            any window opening inside the first repetition stays in range, which makes a
            windowed bit sum one subtraction.
    """

    lfsrs: np.ndarray
    lfsr_to_index: np.ndarray
    bit_prefix: np.ndarray


class LFSRTimer(Timer):
    def __init__(
        self,
        sample_rate: int,
        nes_frequency: int,
        reset_phase: bool = RESET_PHASE,
    ) -> None:
        super().__init__(sample_rate, nes_frequency, reset_phase)

        self._clocks_per_sample: float = 0.0
        self._real_frequency: float = 0.0
        self._period: float = 0.0

        self.short: bool = False

        self.lfsr: int = 1
        self.clock: float = 0.0

        self.lfsr_tables: Dict[bool, LFSRTables] = {
            short: self.precalculate_lfsr_tables(short) for short in (False, True)
        }

    def __call__(
        self,
        initials: Initials = None,
        save: bool = True,
    ) -> np.ndarray:
        self.validate(initials)
        initial_lfsr, initial_clock = initials if initials is not None else (None, None)

        if initial_lfsr is not None:
            self.lfsr = initial_lfsr

        if initial_clock is not None:
            self.clock = initial_clock

        if self._clocks_per_sample <= 0:
            frame = self.prepare_frame(None)
            frame.fill(2.0 * (self.lfsr & 1) - 1.0)
            return frame

        return self.generate_frame(save=save)

    def resolve_index(self, lfsr: int) -> int:
        """The position of a register value within the active mode's cycle.

        Each feedback mode permutes the register into cycles of its own, and short mode's
        93-step cycle holds 93 of the 32767 possible values, so a value carried over from
        long mode sits on a different cycle. Such a value opens the sequence at its start.

        Args:
            lfsr: The register value to locate, 1 to ``MAX_LFSR``.

        Returns:
            int: The value's index on the active cycle, or ``CYCLE_START`` for a value the
                active mode reaches on another cycle.
        """
        index = int(self.lfsr_tables[self.short].lfsr_to_index[lfsr])
        return index if index != OFF_CYCLE else CYCLE_START

    def calculate_offset(self, initials: Initials = None) -> int:
        lfsr, clock = initials if initials is not None else (1, 0.0)
        index = self.resolve_index(lfsr)
        return int(np.ceil(index / self._clocks_per_sample - clock))

    def generate_frame(self, save: bool = True) -> np.ndarray:
        tables = self.lfsr_tables[self.short]
        length = self.lfsr_period
        index = self.resolve_index(self.lfsr)

        samples = np.arange(self.frame_length + 1, dtype=np.float64)
        clocks = samples * self._clocks_per_sample + self.clock
        edges = np.floor(clocks).astype(np.int64)
        starts = edges[:-1]
        steps = edges[1:] - starts

        positions = (index + starts) % length
        held = tables.bit_prefix[positions + 1] - tables.bit_prefix[positions]
        stepped = tables.bit_prefix[positions + steps + 1] - tables.bit_prefix[positions + 1]
        levels = np.where(steps > 0, stepped / np.maximum(steps, 1), held)

        if save:
            self.lfsr = int(tables.lfsrs[(index + int(edges[-1])) % length])
            self.clock = float(clocks[-1] % 1.0)

        frame: np.ndarray = (2.0 * levels - 1.0).astype(np.float32)
        return frame

    @property
    def initials(self) -> Tuple[Any, ...]:
        return self.lfsr, self.clock

    @property
    def period(self) -> float:
        return self._period

    @period.setter
    def period(self, value: int) -> None:
        self._clocks_per_sample = self.calculate_clocks_per_sample(value)
        self._period = self.lfsr_period / self._clocks_per_sample
        self._real_frequency = self.sample_rate / self._period

        if self.reset_phase:
            self.reset()

    def calculate_clocks_per_sample(self, period: int) -> float:
        apu_period = NOISE_PERIODS[period]
        lfsr_clock_hz = APU_CLOCK / float(apu_period)
        return lfsr_clock_hz / float(self.sample_rate)

    def forward(self, lfsr: int) -> int:
        return step_lfsr(lfsr, self.short)

    def backward(self, lfsr: int) -> int:
        return step_lfsr_back(lfsr, self.short)

    def reset(self) -> None:
        self.lfsr = 1
        self.clock = 0.0

    def validate(self, initials: Initials) -> None:
        initial_lfsr, initial_clock = initials if initials is not None else (None, None)
        if initial_lfsr is not None and (
            not isinstance(initial_lfsr, int) or (initial_lfsr < 1 or initial_lfsr > 0x7FFF)
        ):
            raise ValueError("Initial LFSR for LFSRTimer must be between 1 and 0x7FFF")

        if initial_clock is not None and (
            not isinstance(initial_clock, float) or (initial_clock < 0.0 or initial_clock >= 1.0)
        ):
            raise ValueError("Initial clock for LFSRTimer must be between 0.0 and 1.0")

    def get(self) -> Tuple[int, float]:
        return self.lfsr, self.clock

    def set(self, value: Optional[Tuple[int, float]]) -> None:
        if value is None:
            self.reset()
            return

        lfsr, clock = value
        assert isinstance(lfsr, int) and (1 <= lfsr <= 0x7FFF), "LFSR value must be between 1 and 0x7FFF"
        assert isinstance(clock, float) and (0.0 <= clock < 1.0), "Clock value must be between 0.0 and 1.0"
        self.lfsr = lfsr
        self.clock = clock

    def precalculate_lfsr_tables(self, short: bool) -> LFSRTables:
        """Walks one feedback mode's cycle and builds the lookups :meth:`generate_frame` reads.

        Args:
            short: Whether to walk the 93-step short-mode cycle.

        Returns:
            LFSRTables: The cycle's register values, their index lookup and the bit prefix sum.
        """
        length = cycle_length(short)
        lfsrs = np.empty(length, dtype=np.int32)
        lfsr_to_index = np.full(MAX_LFSR + 1, OFF_CYCLE, dtype=np.int32)

        lfsr = 1
        for index in range(length):
            lfsrs[index] = lfsr
            lfsr_to_index[lfsr] = index
            lfsr = step_lfsr(lfsr, short)

        repeats = 1 + int(np.ceil(self.maximum_steps_per_sample / length))
        bits = np.tile(lfsrs & 1, repeats)
        bit_prefix = np.concatenate([[0], np.cumsum(bits)]).astype(np.int32)

        return LFSRTables(
            lfsrs=lfsrs,
            lfsr_to_index=lfsr_to_index,
            bit_prefix=bit_prefix,
        )

    @property
    def maximum_steps_per_sample(self) -> int:
        """The most shift-register steps one output sample spans, at the fastest period."""
        return int(np.ceil(self.calculate_clocks_per_sample(MAX_PERIOD))) + 1

    @property
    def lfsr_period(self) -> int:
        return cycle_length(self.short)
