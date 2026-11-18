from pathlib import Path
from typing import Dict, Final

from assets.stage.runner import pytest_arguments, run_environment
from automation.environment import HOMES_VARIABLE, KEPT_VARIABLE, SCREEN_VARIABLE

SCENES: Final[Path] = Path("/checkout/assets/maker/scenes")
KEPT: Final[Path] = Path("/checkout/build/maker")
HOMES: Final[Path] = Path("/checkout/build/worlds/homes")
SCREEN: Final[str] = "1200x900"
NAMING: Final[Dict[str, str]] = {
    "python_files": "*_shots.py",
    "python_classes": "*Shots",
    "python_functions": "shot_*",
}
MARKER: Final[str] = "slow"
MARKERS: Final[Dict[str, str]] = {MARKER: "a shot that takes its time"}


class TestPytestArguments:
    def test_the_scenes_are_collected_under_their_own_naming(self) -> None:
        arguments = pytest_arguments(SCENES, NAMING, markers=MARKERS, workers="2", selection=f"not {MARKER}")

        assert arguments[0] == str(SCENES)
        for key, value in NAMING.items():
            assert f"{key}={value}" in arguments

    def test_every_naming_rule_travels_as_an_override_beside_each_marker(self) -> None:
        arguments = pytest_arguments(SCENES, NAMING, markers=MARKERS, workers="2", selection=f"not {MARKER}")

        assert arguments.count("-o") == len(NAMING) + len(MARKERS)
        assert f"markers={MARKER}: {MARKERS[MARKER]}" in arguments
        assert arguments[arguments.index("-n") + 1] == "2"
        assert arguments[arguments.index("-m") + 1] == f"not {MARKER}"

    def test_scenes_run_one_at_a_time_take_no_workers(self) -> None:
        arguments = pytest_arguments(SCENES, NAMING, markers=MARKERS, workers=None, selection=MARKER)

        assert "-n" not in arguments
        assert arguments[arguments.index("-m") + 1] == MARKER

    def test_no_selection_picks_every_scene(self) -> None:
        arguments = pytest_arguments(SCENES, NAMING, markers={}, workers=None, selection=None)

        assert "-m" not in arguments
        assert arguments.count("-o") == len(NAMING)


class TestRunEnvironment:
    def test_the_screen_the_kept_records_and_the_homes_are_set(self) -> None:
        environment = run_environment({}, screen=SCREEN, kept=KEPT, homes=HOMES, repository=Path("/checkout"))

        assert environment[SCREEN_VARIABLE] == SCREEN
        assert environment[KEPT_VARIABLE] == str(KEPT)
        assert environment[HOMES_VARIABLE] == str(HOMES)

    def test_a_checkout_under_a_hidden_folder_leaves_the_homes_where_the_plugin_puts_them(self) -> None:
        environment = run_environment({}, screen=SCREEN, kept=KEPT, homes=HOMES, repository=Path("/work/.worktrees/x"))

        assert HOMES_VARIABLE not in environment

    def test_the_temporary_folder_travels_as_it_is(self) -> None:
        environment = run_environment(
            {"TMPDIR": "/tmp"}, screen=SCREEN, kept=KEPT, homes=HOMES, repository=Path("/checkout")
        )

        assert environment["TMPDIR"] == "/tmp"

    def test_the_rest_of_the_environment_travels(self) -> None:
        environment = run_environment(
            {"DISPLAY": ":1"}, screen=SCREEN, kept=KEPT, homes=HOMES, repository=Path("/checkout")
        )

        assert environment["DISPLAY"] == ":1"
