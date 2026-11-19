from typing import Final

import pytest

from assets.footage.schedule import FrameRateError, schedule
from assets.footage.specification import Timeline

TICK_RATE: Final[int] = 60
OPENING: Final[float] = 1.13
CUT: Final[float] = 2.0
ENDING: Final[float] = 3.0
TIMELINE: Final[Timeline] = Timeline.model_validate(
    {
        "start": OPENING,
        "end": ENDING,
        "segments": [
            {"from": OPENING, "audio": "original", "stems": ["Vocals"]},
            {"from": CUT, "audio": "reconstruction", "stems": ["Vocals"]},
        ],
    }
)


class TestSchedule:
    def test_the_footage_opens_on_the_tick_nearest_its_start(self) -> None:
        laid = schedule(TIMELINE, tick_rate=TICK_RATE, frame_rate=TICK_RATE)

        assert laid.first_tick == round(OPENING * TICK_RATE)
        assert laid.tick(0) == laid.first_tick

    def test_each_frame_shows_the_next_tick_at_the_tick_rate(self) -> None:
        laid = schedule(TIMELINE, tick_rate=TICK_RATE, frame_rate=TICK_RATE)

        assert laid.ticks_per_frame == 1
        assert laid.tick(5) == laid.first_tick + 5

    def test_a_lower_frame_rate_shows_every_few_ticks(self) -> None:
        laid = schedule(TIMELINE, tick_rate=TICK_RATE, frame_rate=TICK_RATE // 2)

        assert laid.ticks_per_frame == 2
        assert laid.tick(1) - laid.tick(0) == 2

    def test_a_listening_takes_over_on_the_first_frame_at_or_after_its_segment(self) -> None:
        laid = schedule(TIMELINE, tick_rate=TICK_RATE, frame_rate=TICK_RATE)
        cut_frame = laid.runs[1].first

        assert laid.tick(cut_frame) / TICK_RATE >= CUT
        assert laid.tick(cut_frame - 1) / TICK_RATE < CUT
        assert laid.listening(cut_frame - 1) == TIMELINE.segments[0].listening
        assert laid.listening(cut_frame) == TIMELINE.segments[1].listening

    def test_the_runs_cover_every_frame_once(self) -> None:
        laid = schedule(TIMELINE, tick_rate=TICK_RATE, frame_rate=TICK_RATE)

        assert laid.runs[0].first == 0
        assert all(earlier.last == later.first for earlier, later in zip(laid.runs, laid.runs[1:]))
        assert laid.runs[-1].last == laid.frame_count

    def test_a_frame_rate_the_tick_rate_holds_no_whole_number_of_is_refused(self) -> None:
        with pytest.raises(FrameRateError):
            schedule(TIMELINE, tick_rate=TICK_RATE, frame_rate=25)
