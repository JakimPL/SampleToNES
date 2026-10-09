from pathlib import Path
from typing import Final

from assets.pictures.__main__ import ALONE_MARKER, NAMING, pytest_arguments, run_environment
from automation.environment import HOMES_VARIABLE, KEPT_VARIABLE, SCREEN_VARIABLE

SCENES: Final[Path] = Path("/checkout/assets/pictures/scenes")
KEPT: Final[Path] = Path("/checkout/build/pictures")
HOMES: Final[Path] = Path("/checkout/build/worlds/homes")


class TestPytestArguments:
    def test_the_scenes_are_collected_under_their_own_naming(self) -> None:
        arguments = pytest_arguments(SCENES, NAMING, workers="2", selection=f"not {ALONE_MARKER}")

        assert arguments[0] == str(SCENES)
        assert "python_files=*_scenes.py" in arguments
        assert "python_classes=*Scenes" in arguments
        assert "python_functions=picture_*" in arguments

    def test_every_naming_rule_travels_as_an_override_beside_the_marker(self) -> None:
        arguments = pytest_arguments(SCENES, NAMING, workers="2", selection=f"not {ALONE_MARKER}")

        assert arguments.count("-o") == len(NAMING) + 1
        assert arguments[arguments.index("-n") + 1] == "2"
        assert arguments[arguments.index("-m") + 1] == f"not {ALONE_MARKER}"

    def test_the_scenes_drawn_alone_take_no_workers(self) -> None:
        arguments = pytest_arguments(SCENES, NAMING, workers=None, selection=ALONE_MARKER)

        assert "-n" not in arguments
        assert arguments[arguments.index("-m") + 1] == ALONE_MARKER


class TestRunEnvironment:
    def test_the_screen_the_kept_records_and_the_homes_are_set(self) -> None:
        environment = run_environment({}, kept=KEPT, homes=HOMES, repository=Path("/checkout"))

        assert environment[SCREEN_VARIABLE] == "1700x1300"
        assert environment[KEPT_VARIABLE] == str(KEPT)
        assert environment[HOMES_VARIABLE] == str(HOMES)

    def test_a_checkout_under_a_hidden_folder_leaves_the_homes_where_the_plugin_puts_them(self) -> None:
        environment = run_environment({}, kept=KEPT, homes=HOMES, repository=Path("/work/.worktrees/x"))

        assert HOMES_VARIABLE not in environment

    def test_the_temporary_folder_travels_as_it_is(self) -> None:
        environment = run_environment({"TMPDIR": "/tmp"}, kept=KEPT, homes=HOMES, repository=Path("/checkout"))

        assert environment["TMPDIR"] == "/tmp"

    def test_the_rest_of_the_environment_travels(self) -> None:
        environment = run_environment({"DISPLAY": ":1"}, kept=KEPT, homes=HOMES, repository=Path("/checkout"))

        assert environment["DISPLAY"] == ":1"
