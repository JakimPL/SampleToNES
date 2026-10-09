import pytest
from pydantic import ValidationError

from sampletones_application.config.session.application.tracker import TrackerConfig
from sampletones_application.constants.tracker import MAX_OCTAVE, MIN_OCTAVE


class TestOctaveBounds:
    """The typing octave is held to the range the tracker's own octave field offers."""

    @pytest.mark.parametrize("octave", [MIN_OCTAVE - 1, MAX_OCTAVE + 1])
    def test_an_octave_outside_the_range_is_rejected(self, octave: int) -> None:
        with pytest.raises(ValidationError):
            TrackerConfig(octave=octave)

    @pytest.mark.parametrize("octave", [MIN_OCTAVE, MAX_OCTAVE])
    def test_each_end_of_the_range_is_accepted(self, octave: int) -> None:
        config = TrackerConfig(octave=octave)

        assert config.octave == octave
