from pathlib import Path
from typing import Final

from assets.pictures.__main__ import NAMING, pytest_arguments, run_environment
from automation.environment import KEPT_VARIABLE, SCREEN_VARIABLE

SCENES: Final[Path] = Path("/checkout/assets/pictures/scenes")
KEPT: Final[Path] = Path("/checkout/build/pictures")
HOMES: Final[Path] = KEPT / "homes"


class TestPytestArguments:
    def test_the_scenes_are_collected_under_their_own_naming(self) -> None:
        arguments = pytest_arguments(SCENES, NAMING, "2")

        assert arguments[0] == str(SCENES)
        assert "python_files=*_scenes.py" in arguments
        assert "python_classes=*Scenes" in arguments
        assert "python_functions=picture_*" in arguments

    def test_every_naming_rule_travels_as_an_override(self) -> None:
        arguments = pytest_arguments(SCENES, NAMING, "2")

        assert arguments.count("-o") == len(NAMING)
        assert arguments[arguments.index("-n") + 1] == "2"


class TestRunEnvironment:
    def test_the_screen_and_the_kept_records_are_set(self) -> None:
        environment = run_environment({}, kept=KEPT, homes=HOMES, repository=Path("/checkout"))

        assert environment[SCREEN_VARIABLE] == "1700x1300"
        assert environment[KEPT_VARIABLE] == str(KEPT)
        assert environment["TMPDIR"] == str(HOMES)

    def test_a_checkout_under_a_hidden_folder_keeps_the_system_s_temporary_folder(self) -> None:
        environment = run_environment({"TMPDIR": "/tmp"}, kept=KEPT, homes=HOMES, repository=Path("/work/.worktrees/x"))

        assert environment["TMPDIR"] == "/tmp"

    def test_the_rest_of_the_environment_travels(self) -> None:
        environment = run_environment({"DISPLAY": ":1"}, kept=KEPT, homes=HOMES, repository=Path("/checkout"))

        assert environment["DISPLAY"] == ":1"
