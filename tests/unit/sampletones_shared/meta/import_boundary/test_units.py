from sampletones_shared.meta.import_boundary.units import nested_globs, unit_glob, unit_prefix

PLAYER = "sampletones_player"


class TestUnitGlobs:
    """A unit names either one module or a directory of them, and reads as both."""

    def test_a_directory_unit_reaches_every_module_below_it(self) -> None:
        assert unit_glob("driver") == "driver/**/*.py"

    def test_a_module_unit_names_itself(self) -> None:
        assert unit_glob("song.py") == "song.py"

    def test_a_nested_unit_is_named_as_the_glob_it_owns(self) -> None:
        assert nested_globs("driver", ("driver", "driver/assembler", "clock")) == ("driver/assembler/**/*.py",)

    def test_a_unit_beside_another_is_left_to_itself(self) -> None:
        assert nested_globs("clock", ("driver", "driver/assembler", "clock")) == ()


class TestUnitPrefixes:
    """The dotted prefix an import of a unit begins with."""

    def test_a_unit_under_a_package_is_reached_by_a_dotted_prefix(self) -> None:
        assert unit_prefix(PLAYER, "driver/assembler") == "sampletones_player.driver.assembler"

    def test_a_module_unit_drops_its_suffix(self) -> None:
        assert unit_prefix(PLAYER, "song.py") == "sampletones_player.song"

    def test_a_package_unit_is_reached_by_its_own_name(self) -> None:
        assert unit_prefix("", "sampletones_core") == "sampletones_core"
