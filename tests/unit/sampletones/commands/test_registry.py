import json
import subprocess
import sys
from importlib.util import find_spec
from typing import Final, List, Tuple

import pytest

from sampletones.commands.registry import COMMANDS, USER_COMMANDS
from sampletones.dispatcher import DEFAULT_COMMAND, build_parser
from sampletones_tools.registry import DEVELOPER_COMMANDS

TOOLS_PACKAGE: Final[str] = "sampletones_tools"
FACE_MODULES: Final[Tuple[str, ...]] = ("command", "registry")
FACE_PACKAGE: Final[str] = "commands"
HEAVY_MODULES: Final[Tuple[str, ...]] = (
    "numpy",
    "scipy",
    "librosa",
    "cupy",
    "PIL",
    "py65",
    "pytest",
    "dearpygui",
    "sampletones_shared.paths.user",
)
PROBE: Final[str] = "import json, sys, sampletones.commands.registry; print(json.dumps(sorted(sys.modules)))"


def _is_face(module: str) -> bool:
    """Whether a tools module is one a command list reads: a package initializer, a command, a
    registry, or a module under ``commands``."""
    spec = find_spec(module)
    parts = module.split(".")
    return (
        (spec is not None and spec.submodule_search_locations is not None)
        or parts[-1] in FACE_MODULES
        or FACE_PACKAGE in parts[:-1]
    )


@pytest.fixture(scope="module")
def loaded_modules() -> List[str]:
    """Every module a fresh interpreter holds once it lists the commands."""
    completed = subprocess.run(
        [sys.executable, "-c", PROBE],
        check=True,
        capture_output=True,
        text=True,
    )
    modules: List[str] = json.loads(completed.stdout)
    return modules


class TestRegistry:
    def test_the_user_commands_are_the_ones_the_guide_names(self) -> None:
        assert [command.name for command in USER_COMMANDS] == ["run", "open", "convert", "library", "self-check"]

    def test_the_commands_are_the_user_ones_followed_by_the_developer_ones(self) -> None:
        assert COMMANDS == (*USER_COMMANDS, *DEVELOPER_COMMANDS)

    def test_the_default_command_is_registered(self) -> None:
        assert DEFAULT_COMMAND in {command.name for command in COMMANDS}

    def test_the_registry_builds_one_parser(self) -> None:
        assert build_parser(COMMANDS).format_help()


class TestListingTheCommands:
    """A module a tool needs, loaded with the command list, would slow and could break every invocation, the GUI included."""

    def test_only_the_faces_of_the_tools_are_loaded(self, loaded_modules: List[str]) -> None:
        tools = [module for module in loaded_modules if module.startswith(f"{TOOLS_PACKAGE}.")]

        assert tools
        assert [module for module in tools if not _is_face(module)] == []

    def test_no_heavy_module_is_loaded(self, loaded_modules: List[str]) -> None:
        assert set(loaded_modules) & set(HEAVY_MODULES) == set()
