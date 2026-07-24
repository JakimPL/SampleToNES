import numpy as np
import pytest

from sampletones_core.timers.implementation.phase import PhaseTimer

INVALID_PHASE_INITIALS = [
    ((-0.1,), "phase_negative"),
    ((1.0,), "phase_equals_one"),
    ((0,), "phase_int_type"),
]


@pytest.fixture
def phase_timer() -> PhaseTimer:
    return PhaseTimer(sample_rate=44100, nes_frequency=60)


class TestFrequencyToTimer:
    @pytest.mark.parametrize(
        "frequency, expected",
        [
            (0, 0),
            (-1.0, 0),
            (440.0, 253),
            (0.001, 0x7FF),
            (1e9, 0),
        ],
        ids=["zero_frequency", "negative_frequency", "a4_440hz", "very_low_clamps_at_max", "very_high_clamps_at_zero"],
    )
    def test_timer_value_correct(self, frequency: float, expected: int) -> None:
        assert PhaseTimer.frequency_to_timer(frequency) == expected


class TestGetTimerTicks:
    @pytest.mark.parametrize(
        "timer, expected",
        [
            (0, 0),
            (-1, 0),
            (1, 32),
            (100, 1616),
        ],
        ids=["zero_returns_zero", "negative_returns_zero", "timer_1_gives_32", "timer_100_gives_1616"],
    )
    def test_tick_count_correct(self, timer: int, expected: int) -> None:
        assert PhaseTimer.get_timer_ticks(timer) == expected


class TestPhaseTimerValidate:
    @pytest.mark.parametrize(
        "initials",
        [initials for initials, _ in INVALID_PHASE_INITIALS],
        ids=[label for _, label in INVALID_PHASE_INITIALS],
    )
    def test_invalid_initials_raise(self, phase_timer: PhaseTimer, initials: tuple) -> None:
        with pytest.raises(ValueError):
            phase_timer.validate(initials)

    def test_none_initials_do_not_raise(self, phase_timer: PhaseTimer) -> None:
        phase_timer.validate(None)

    def test_minimum_valid_phase_does_not_raise(self, phase_timer: PhaseTimer) -> None:
        phase_timer.validate((0.0,))

    def test_near_maximum_valid_phase_does_not_raise(self, phase_timer: PhaseTimer) -> None:
        phase_timer.validate((0.9999,))


class TestPhaseTimerStateManagement:
    def test_get_returns_current_phase(self, phase_timer: PhaseTimer) -> None:
        phase_timer.phase = 0.5
        assert phase_timer.get() == (0.5,)

    def test_set_restores_given_phase(self, phase_timer: PhaseTimer) -> None:
        phase_timer.set((0.7,))
        assert phase_timer.phase == 0.7

    def test_set_none_resets_phase(self, phase_timer: PhaseTimer) -> None:
        phase_timer.phase = 0.5
        phase_timer.set(None)
        assert phase_timer.phase == 0.0

    def test_reset_sets_phase_to_zero(self, phase_timer: PhaseTimer) -> None:
        phase_timer.phase = 0.5
        phase_timer.reset()
        assert phase_timer.phase == 0.0


class TestPhaseTimerCall:
    def test_unconfigured_returns_constant_frame(self, phase_timer: PhaseTimer) -> None:
        frame = phase_timer()
        assert np.all(frame == frame[0])

    def test_unconfigured_returns_frame_of_correct_length(self, phase_timer: PhaseTimer) -> None:
        frame = phase_timer()
        assert len(frame) == phase_timer.frame_length

    def test_configured_returns_frame_of_correct_length(self, phase_timer: PhaseTimer) -> None:
        phase_timer.frequency = 440.0
        frame = phase_timer()
        assert len(frame) == phase_timer.frame_length

    def test_initials_override_phase_before_render(self, phase_timer: PhaseTimer) -> None:
        phase_timer.frequency = 440.0
        phase_timer((0.5,), save=False)
        assert phase_timer.phase == 0.5


class TestPhaseTimerGenerateFrameSaveFlag:
    def test_save_false_does_not_advance_phase(self, phase_timer: PhaseTimer) -> None:
        phase_timer.frequency = 440.0
        phase_before = phase_timer.phase
        phase_timer.generate_frame(save=False)
        assert phase_timer.phase == phase_before

    def test_save_true_advances_phase(self, phase_timer: PhaseTimer) -> None:
        phase_timer.frequency = 440.0
        phase_before = phase_timer.phase
        phase_timer.generate_frame(save=True)
        assert phase_timer.phase != phase_before


class TestPhaseTimerProperties:
    def test_initials_reflects_current_phase(self, phase_timer: PhaseTimer) -> None:
        phase_timer.phase = 0.5
        assert phase_timer.initials == (0.5,)


class TestPhaseTimerResetPhase:
    def test_frequency_setter_resets_phase_when_reset_phase_true(self) -> None:
        timer = PhaseTimer(sample_rate=44100, nes_frequency=60, reset_phase=True)
        timer.phase = 0.5
        timer.frequency = 440.0
        assert timer.phase == 0.0
