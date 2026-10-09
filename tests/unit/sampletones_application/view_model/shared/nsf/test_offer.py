from sampletones_application.view_model.shared.nsf.offer import FIRST_FRAME
from sampletones_application.view_model.shared.nsf.repeat import NSFRepeat
from tests.suite.nsf import ORDER_FRAMES, project_offer, sample_offer


class TestTheRepeatsFollowTheFrames:
    def test_a_song_laid_out_in_frames_repeats_from_any_of_them(self) -> None:
        assert NSFRepeat.FROM_FRAME in project_offer().repeats

    def test_a_song_without_frames_repeats_from_its_start_or_plays_once(self) -> None:
        assert sample_offer().repeats == (NSFRepeat.ONCE, NSFRepeat.FROM_START)

    def test_the_last_frame_is_the_orders_last(self) -> None:
        assert project_offer().last_frame == ORDER_FRAMES - 1

    def test_a_song_without_frames_returns_to_the_first(self) -> None:
        assert sample_offer().last_frame == FIRST_FRAME
