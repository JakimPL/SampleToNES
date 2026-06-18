from dataclasses import dataclass

import numpy as np
import pytest

from sampletones_core.constants.general import MAX_LFSR, MAX_LFSR_SHORT
from sampletones_core.timers.implementation.lfsr import LFSRTimer
from tests.suite.case import BaseTestCase


@dataclass(frozen=True, kw_only=True)
class LFSRForwardCase(BaseTestCase):
    label: str
    input_lfsr: int
    expected: int


@pytest.fixture
def long_timer() -> LFSRTimer:
    timer = LFSRTimer(sample_rate=44100, change_rate=60)
    timer.short = False
    return timer


@pytest.fixture
def short_timer() -> LFSRTimer:
    timer = LFSRTimer(sample_rate=44100, change_rate=60)
    timer.short = True
    return timer


LONG_FORWARD_CASES = [
    LFSRForwardCase(label="initial 1 to 16384", input_lfsr=1, expected=16384),
    LFSRForwardCase(label="16384 to 8192", input_lfsr=16384, expected=8192),
]

SHORT_FORWARD_CASES = [
    LFSRForwardCase(label="initial 1 to 16384", input_lfsr=1, expected=16384),
    LFSRForwardCase(label="64 has bit-6 feedback", input_lfsr=64, expected=16416),
]

INVALID_INITIALS = [
    ((0, 0.0), "lfsr_zero"),
    ((0x8000, 0.0), "lfsr_above_max"),
    ((1.0, 0.0), "lfsr_float_type"),
    ((1, -0.1), "clock_negative"),
    ((1, 1.0), "clock_equals_one"),
    ((1, 0), "clock_int_type"),
]


class TestLFSRForwardLong:
    @pytest.mark.parametrize("case", LONG_FORWARD_CASES, ids=lambda c: c.label)
    def test_forward_advances_correctly(self, long_timer: LFSRTimer, case: LFSRForwardCase) -> None:
        assert long_timer.forward(case.input_lfsr) == case.expected


class TestLFSRForwardShort:
    @pytest.mark.parametrize("case", SHORT_FORWARD_CASES, ids=lambda c: c.label)
    def test_forward_advances_correctly(self, short_timer: LFSRTimer, case: LFSRForwardCase) -> None:
        assert short_timer.forward(case.input_lfsr) == case.expected


class TestLFSRRoundtrip:
    def test_backward_inverts_forward_in_long_mode(self, long_timer: LFSRTimer) -> None:
        assert long_timer.backward(long_timer.forward(1)) == 1

    def test_backward_inverts_forward_in_short_mode(self, short_timer: LFSRTimer) -> None:
        assert short_timer.backward(short_timer.forward(1)) == 1


class TestLFSRPeriod:
    def test_long_period_is_max_lfsr(self, long_timer: LFSRTimer) -> None:
        visited = [1]
        lfsr = long_timer.forward(1)
        while lfsr != 1:
            visited.append(lfsr)
            lfsr = long_timer.forward(lfsr)

        assert len(visited) == MAX_LFSR
        assert len(set(visited)) == MAX_LFSR

    def test_short_period_is_max_lfsr_short(self, short_timer: LFSRTimer) -> None:
        visited = [1]
        lfsr = short_timer.forward(1)
        while lfsr != 1:
            visited.append(lfsr)
            lfsr = short_timer.forward(lfsr)

        assert len(visited) == MAX_LFSR_SHORT
        assert len(set(visited)) == MAX_LFSR_SHORT


class TestLFSRValidate:
    @pytest.mark.parametrize(
        "initials",
        [initials for initials, _ in INVALID_INITIALS],
        ids=[label for _, label in INVALID_INITIALS],
    )
    def test_invalid_initials_raise(self, long_timer: LFSRTimer, initials: tuple) -> None:
        with pytest.raises(ValueError):
            long_timer.validate(initials)

    def test_minimum_valid_initials_do_not_raise(self, long_timer: LFSRTimer) -> None:
        long_timer.validate((1, 0.0))

    def test_maximum_valid_initials_do_not_raise(self, long_timer: LFSRTimer) -> None:
        long_timer.validate((0x7FFF, 0.9999))


class TestLFSRStateManagement:
    def test_get_returns_current_lfsr_and_clock(self, long_timer: LFSRTimer) -> None:
        long_timer.lfsr = 100
        long_timer.clock = 0.5
        assert long_timer.get() == (100, 0.5)

    def test_set_restores_given_state(self, long_timer: LFSRTimer) -> None:
        long_timer.set((200, 0.3))
        assert long_timer.lfsr == 200
        assert long_timer.clock == 0.3

    def test_set_none_resets_to_initial(self, long_timer: LFSRTimer) -> None:
        long_timer.lfsr = 100
        long_timer.clock = 0.5
        long_timer.set(None)
        assert long_timer.get() == (1, 0.0)

    def test_reset_restores_initial_state(self, long_timer: LFSRTimer) -> None:
        long_timer.lfsr = 500
        long_timer.clock = 0.7
        long_timer.reset()
        assert long_timer.lfsr == 1
        assert long_timer.clock == 0.0


class TestLFSRCall:
    def test_unconfigured_returns_constant_frame(self, long_timer: LFSRTimer) -> None:
        frame = long_timer()
        assert np.all(frame == frame[0])

    def test_unconfigured_returns_frame_of_correct_length(self, long_timer: LFSRTimer) -> None:
        frame = long_timer()
        assert len(frame) == long_timer.frame_length

    def test_configured_returns_frame_of_correct_length(self, long_timer: LFSRTimer) -> None:
        long_timer.period = 7
        frame = long_timer()
        assert len(frame) == long_timer.frame_length

    def test_initials_override_lfsr_before_render(self, long_timer: LFSRTimer) -> None:
        long_timer.period = 7
        long_timer((500, 0.0), save=False)
        assert long_timer.lfsr == 500

    def test_initials_override_clock_before_render(self, long_timer: LFSRTimer) -> None:
        long_timer.period = 7
        long_timer((500, 0.3), save=False)
        assert long_timer.clock == 0.3


class TestLFSRGenerateFrameSaveFlag:
    def test_save_false_does_not_advance_lfsr(self, long_timer: LFSRTimer) -> None:
        long_timer.period = 7
        state_before = long_timer.get()
        long_timer.generate_frame(save=False)
        assert long_timer.get() == state_before

    def test_save_true_advances_lfsr(self, long_timer: LFSRTimer) -> None:
        long_timer.period = 7
        state_before = long_timer.get()
        long_timer.generate_frame(save=True)
        assert long_timer.get() != state_before


class TestLFSRProperties:
    def test_initials_reflects_current_state(self, long_timer: LFSRTimer) -> None:
        long_timer.lfsr = 100
        long_timer.clock = 0.3
        assert long_timer.initials == (100, 0.3)

    def test_period_getter_returns_positive_after_setting(self, long_timer: LFSRTimer) -> None:
        long_timer.period = 7
        assert long_timer.period > 0

    def test_real_frequency_positive_after_period_set(self, long_timer: LFSRTimer) -> None:
        long_timer.period = 7
        assert long_timer.real_frequency > 0


class TestLFSRResetPhase:
    def test_period_setter_resets_state_when_reset_phase_true(self) -> None:
        timer = LFSRTimer(sample_rate=44100, change_rate=60, reset_phase=True)
        timer.lfsr = 500
        timer.clock = 0.5
        timer.period = 7
        assert timer.lfsr == 1
        assert timer.clock == 0.0
