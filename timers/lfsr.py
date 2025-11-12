from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import numpy as np

from constants.general import (
    APU_CLOCK,
    MAX_LFSR,
    MAX_LFSR_SHORT,
    MAX_PERIOD,
    NOISE_PERIODS,
    RESET_PHASE,
)
from typehints import Initials

from .timer import Timer


@dataclass(frozen=True)
class LFSRTTables:
    lfsr_to_index: np.ndarray
    lfsrs: Dict[bool, np.ndarray]
    cumsums: Dict[bool, np.ndarray]


class LFSRTimer(Timer):
    def __init__(self, sample_rate: int, change_rate: int, reset_phase: bool = RESET_PHASE) -> None:
        super().__init__(sample_rate, change_rate, reset_phase)

        self._clocks_per_sample: float = 0.0
        self._real_frequency: float = 0.0
        self._period: float = 0.0

        self.short: bool = False

        self.lfsr: int = 1
        self.clock: float = 0.0

        self.lfsr_tables: Dict[bool, LFSRTTables] = {
            True: self.precalculate_lfsr_tables(True),
            False: self.precalculate_lfsr_tables(False),
        }

    def __call__(
        self,
        initials: Initials = None,
    ) -> np.ndarray:
        initial_lfsr, initial_clock = initials if initials is not None else (None, None)
        self.validate(initial_lfsr, initial_clock)

        if initial_lfsr is not None:
            self.lfsr = initial_lfsr

        if initial_clock is not None:
            self.clock = initial_clock

        if self._clocks_per_sample <= 0:
            frame = self.prepare_frame(None)
            frame.fill(2.0 * (self.lfsr & 1) - 1.0)
            return frame

        return self.generate_frame()

    def calculate_offset(self, initials: Initials = None) -> int:
        lfsr, clock = initials if initials is not None else (1, 0.0)
        lfsr_to_index = self.lfsr_tables[self.short].lfsr_to_index
        end_index = int(lfsr_to_index[lfsr])
        if end_index == -1:
            end_index = 0

        return int(np.ceil(end_index / self._clocks_per_sample - clock))

    def generate_frame(self, direction: bool = True, save: bool = True) -> np.ndarray:
        lfsrs = self.lfsr_tables[self.short].lfsrs[direction]
        cumsum_table = self.lfsr_tables[self.short].cumsums[direction].astype(np.float32)

        indices = np.arange(self.frame_length + 1)
        sign = 1.0 if direction else -1.0
        delta = self._clocks_per_sample * sign
        clock = indices * delta + self.clock
        changes = np.abs(np.diff(np.floor(clock)).astype(int))
        changes_cumsum = np.concatenate([[0], np.cumsum(changes)])
        differences = np.zeros_like(changes, dtype=np.float32)

        index = self.lfsr_tables[self.short].lfsr_to_index[self.lfsr]
        index = index if index != -1 else 0
        start_indices = changes_cumsum + index
        end_indices = np.roll(start_indices, -1)
        pairs = np.stack([start_indices, end_indices]).T[:-1]
        mask = pairs[:, 0] > pairs[:, 1]
        pairs[mask, 1] += self.lfsr_period

        mask = pairs[:, 1] > pairs[:, 0]
        nonzero_pairs = pairs[mask]
        means = np.array([np.mean(cumsum_table[pair[0] : pair[1]]) for pair in nonzero_pairs])

        differences[mask] = np.diff(np.concatenate([[0], means]))
        frame = 2.0 * np.cumsum(differences) - 1.0

        if save:
            self.lfsr = int(lfsrs[index + changes_cumsum[-1]])
            self.clock = float(clock[-1] % 1.0)

        return frame if direction else frame[::-1]

    @property
    def initials(self) -> Tuple[Any, ...]:
        return self.lfsr, self.clock

    @property
    def period(self) -> float:
        return self._period

    @period.setter
    def period(self, value: int) -> None:
        self._period = value
        self._clocks_per_sample = self.calculate_clocks_per_sample(value)

        self._period = (93.0 if self.short else 32767.0) / self._clocks_per_sample
        self._real_frequency = self.sample_rate / self._period

        if self.reset_phase:
            self.reset()

    def calculate_clocks_per_sample(self, period: int) -> float:
        apu_period = NOISE_PERIODS[period]
        lfsr_clock_hz = APU_CLOCK / float(apu_period)
        return 2.0 * lfsr_clock_hz / float(self.sample_rate)

    def forward(self, lfsr: int) -> int:
        bit0 = lfsr & 1
        bitX = (lfsr >> (6 if self.short else 1)) & 1
        feedback = bit0 ^ bitX
        lfsr = (lfsr >> 1) | (feedback << 14)
        lfsr &= MAX_LFSR
        return lfsr

    def backward(self, lfsr: int) -> int:
        msb = (lfsr >> 14) & 1
        partial = (lfsr & 0x3FFF) << 1
        bitX = (partial >> (6 if self.short else 1)) & 1
        bit0 = msb ^ bitX
        lfsr = partial | bit0
        lfsr &= MAX_LFSR
        return lfsr

    def reset(self) -> None:
        self.lfsr = 1
        self.clock = 0.0

    def validate(self, initial_lfsr: Optional[int], initial_clock: Optional[float]) -> None:
        if initial_lfsr is not None:
            if not isinstance(initial_lfsr, int) or (initial_lfsr < 1 or initial_lfsr > 0x7FFF):
                raise ValueError(f"Initial LFSR for LFSRTimer must be between 1 and 0x7FFF")

        if initial_clock is not None:
            if not isinstance(initial_clock, float) or (initial_clock < 0.0 or initial_clock >= 1.0):
                raise ValueError(f"Initial clock for LFSRTimer must be between 0.0 and 1.0")

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

    def precalculate_lfsr_tables(self, short: bool) -> LFSRTTables:
        self.short = short
        clocks_per_sample = self.calculate_clocks_per_sample(MAX_PERIOD)
        repeats = int(np.ceil(clocks_per_sample * self.frame_length / self.lfsr_period)) * 2 + 1

        forward_lfsrs = np.ones(MAX_LFSR, dtype=np.int16)
        lfsr_to_index = -np.ones(MAX_LFSR + 1, dtype=np.int16)

        lfsr = 1
        for i in range(MAX_LFSR):
            lfsr_to_index[lfsr] = lfsr_to_index[lfsr] if lfsr_to_index[lfsr] != -1 else i

            forward_lfsr = self.forward(lfsr)
            if i == MAX_LFSR - 1:
                break

            forward_lfsrs[i + 1] = forward_lfsr
            lfsr = forward_lfsr

        forward_lfsrs = np.tile(forward_lfsrs, repeats)
        backward_lfsrs = np.roll(np.flip(forward_lfsrs), 1)
        forward_lfsrs_cumsums = np.concatenate([[0], np.cumsum(forward_lfsrs, dtype=np.int64)]) & 1
        backward_lfsrs_cumsums = np.concatenate([[0], np.cumsum(backward_lfsrs, dtype=np.int64)]) & 1

        return LFSRTTables(
            lfsr_to_index=lfsr_to_index,
            lfsrs={True: forward_lfsrs, False: backward_lfsrs},
            cumsums={True: forward_lfsrs_cumsums, False: backward_lfsrs_cumsums},
        )

    @property
    def lfsr_period(self) -> int:
        return MAX_LFSR_SHORT if self.short else MAX_LFSR
