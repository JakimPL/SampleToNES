import pytest

from sampletones_application.view_model.shared.nearest import nearest_offered


class TestNearestOffered:
    def test_an_offered_value_selects_itself(self) -> None:
        assert nearest_offered(48000, (8000, 44100, 48000)) == 48000

    def test_a_value_between_offers_selects_the_closer_one(self) -> None:
        assert nearest_offered(96000, (8000, 44100, 48000)) == 48000

    def test_two_offers_equally_close_select_the_smaller(self) -> None:
        assert nearest_offered(30, (20, 40)) == 20

    def test_nothing_offered_reports_the_empty_choice(self) -> None:
        with pytest.raises(ValueError):
            nearest_offered(44100, ())
