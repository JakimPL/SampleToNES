from typing import List

import pytest

from sampletones_application.utils.frame_limiter import FrameLimiter

SLEEP = "sampletones_application.utils.frame_limiter.time.sleep"
PERF_COUNTER = "sampletones_application.utils.frame_limiter.time.perf_counter"


@pytest.fixture
def sleeps(monkeypatch: pytest.MonkeyPatch) -> List[float]:
    recorded: List[float] = []
    monkeypatch.setattr(SLEEP, recorded.append)
    return recorded


def _advance(monkeypatch: pytest.MonkeyPatch, times: List[float]) -> None:
    remaining = list(times)
    monkeypatch.setattr(PERF_COUNTER, lambda: remaining.pop(0))


class TestPacing:
    def test_the_first_frame_sleeps_out_nothing(
        self,
        sleeps: List[float],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _advance(monkeypatch, [0.0])
        limiter = FrameLimiter(60)

        limiter.tick()

        assert sleeps == []

    def test_a_frame_arriving_early_sleeps_out_the_rest_of_its_budget(
        self,
        sleeps: List[float],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _advance(monkeypatch, [0.0, 0.005])
        limiter = FrameLimiter(100)

        limiter.tick()
        limiter.tick()

        assert sleeps == [pytest.approx(0.005)]

    def test_a_frame_arriving_late_sleeps_out_nothing(
        self,
        sleeps: List[float],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _advance(monkeypatch, [0.0, 1.0])
        limiter = FrameLimiter(60)

        limiter.tick()
        limiter.tick()

        assert sleeps == []

    def test_an_unlimited_rate_leaves_pacing_to_the_hardware(
        self,
        sleeps: List[float],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _advance(monkeypatch, [])
        limiter = FrameLimiter(0)

        limiter.tick()
        limiter.tick()

        assert sleeps == []


class TestSetMaxFps:
    def test_a_new_rate_paces_the_frames_that_follow(
        self,
        sleeps: List[float],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _advance(monkeypatch, [0.0, 0.001, 0.006])
        limiter = FrameLimiter(1000)
        limiter.tick()

        limiter.set_max_fps(100)
        limiter.tick()
        limiter.tick()

        assert sleeps == [pytest.approx(0.005)]

    def test_lifting_the_cap_stops_the_pacing(
        self,
        sleeps: List[float],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _advance(monkeypatch, [0.0])
        limiter = FrameLimiter(60)
        limiter.tick()

        limiter.set_max_fps(0)
        limiter.tick()

        assert sleeps == []

    def test_the_first_frame_after_a_change_is_timed_from_then(
        self,
        sleeps: List[float],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A frame that spans the change is paced by the new budget alone, never the old one."""
        _advance(monkeypatch, [0.0, 10.0])
        limiter = FrameLimiter(60)
        limiter.tick()

        limiter.set_max_fps(30)
        limiter.tick()

        assert sleeps == []
