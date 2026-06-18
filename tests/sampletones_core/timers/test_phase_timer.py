import pytest

from sampletones_core.constants.general import APU_CLOCK
from sampletones_core.timers.implementation.phase import PhaseTimer


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


class TestTimerToFrequency:
    @pytest.mark.parametrize(
        "timer, expected",
        [
            (0, 0.0),
            (-1, 0.0),
        ],
        ids=["zero_timer_returns_zero", "negative_timer_returns_zero"],
    )
    def test_zero_or_negative_returns_zero(self, timer: int, expected: float) -> None:
        assert PhaseTimer.timer_to_frequency(timer) == expected

    def test_timer_253_gives_approx_440hz(self) -> None:
        assert PhaseTimer.timer_to_frequency(253) == pytest.approx(APU_CLOCK / (16 * 254))


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
