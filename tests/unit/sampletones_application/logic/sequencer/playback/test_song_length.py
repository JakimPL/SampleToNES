from typing import Final

from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.sequencer.playback.synthesizer import SongLength
from sampletones_application.logic.sequencer.playback.synthesizer.timing import SongTiming

FRACTIONAL_RATE: Final[int] = 22050
EXACT_RATE: Final[int] = 44100


def measure(controller: ProjectController, sample_rate: int) -> SongLength:
    return SongLength.measure(controller.project, sample_rate=sample_rate)


class TestTheOrderStatesTheTicks:
    def test_the_song_lasts_its_groove_once_for_each_order_position(
        self,
        controller: ProjectController,
    ) -> None:
        groove = SongTiming.from_project(controller.project).groove()

        length = measure(controller, EXACT_RATE)

        assert length.ticks == controller.project.song.order_length() * groove.total_ticks

    def test_appending_a_frame_lengthens_the_song_by_a_pattern(
        self,
        controller: ProjectController,
    ) -> None:
        before = measure(controller, EXACT_RATE)
        groove = SongTiming.from_project(controller.project).groove()

        controller.append_frame()

        assert measure(controller, EXACT_RATE).ticks == before.ticks + groove.total_ticks


class TestTheRateStatesTheSamples:
    """The clock spreads a fractional samples-per-tick across ticks, so a total lands on the exact
    duration whatever rate it is rendered at."""

    def test_a_rate_dividing_evenly_gives_a_whole_frame_for_every_tick(
        self,
        controller: ProjectController,
    ) -> None:
        length = measure(controller, EXACT_RATE)
        nes_frequency = controller.project.settings.nes_frequency

        assert length.samples == length.ticks * EXACT_RATE // nes_frequency

    def test_a_rate_dividing_fractionally_still_lands_on_the_exact_duration(
        self,
        controller: ProjectController,
    ) -> None:
        length = measure(controller, FRACTIONAL_RATE)
        nes_frequency = controller.project.settings.nes_frequency

        assert length.samples == length.ticks * FRACTIONAL_RATE // nes_frequency
        assert length.samples * 2 - measure(controller, EXACT_RATE).samples <= 1

    def test_a_song_plays_for_the_same_time_at_every_rate(
        self,
        controller: ProjectController,
    ) -> None:
        fractional = measure(controller, FRACTIONAL_RATE)
        exact = measure(controller, EXACT_RATE)

        assert abs(fractional.samples / FRACTIONAL_RATE - exact.samples / EXACT_RATE) < 1e-3
