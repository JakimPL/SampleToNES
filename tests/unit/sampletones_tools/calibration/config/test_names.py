import pytest

from sampletones_tools.calibration.config.names import require_unique_names


class TestRequireUniqueNames:
    def test_names_of_their_own_pass(self) -> None:
        require_unique_names(["first", "second"], "chord")

    def test_no_names_pass(self) -> None:
        require_unique_names([], "chord")

    def test_a_name_given_twice_is_refused_naming_the_kind(self) -> None:
        with pytest.raises(ValueError, match="Every written sequence must have a name of its own"):
            require_unique_names(["tune", "bass", "tune"], "written sequence")
