import subprocess
import sys
from typing import Final, Tuple

from sampletones.commands.registry import COMMANDS, USER_COMMANDS
from sampletones.dispatcher import DEFAULT_COMMAND, build_parser
from sampletones_tools.registry import DEVELOPER_COMMANDS

HEAVY_PACKAGES: Final[Tuple[str, ...]] = ("PIL", "py65", "pytest", "dearpygui")
PROBE: Final[str] = "import sys, sampletones.commands.registry; print(sorted(set(sys.modules) & set(sys.argv[1:])))"


class TestRegistry:
    def test_the_user_commands_are_the_ones_the_guide_names(self) -> None:
        assert [command.name for command in USER_COMMANDS] == ["run", "open", "convert", "library", "self-check"]

    def test_the_commands_are_the_user_ones_followed_by_the_developer_ones(self) -> None:
        assert COMMANDS == (*USER_COMMANDS, *DEVELOPER_COMMANDS)

    def test_the_default_command_is_registered(self) -> None:
        assert DEFAULT_COMMAND in {command.name for command in COMMANDS}

    def test_the_registry_builds_one_parser(self) -> None:
        assert build_parser(COMMANDS).format_help()

    def test_listing_the_commands_loads_no_tool(self) -> None:
        """A tool's dependency imported at module level would break every invocation, the GUI included."""
        completed = subprocess.run(
            [sys.executable, "-c", PROBE, *HEAVY_PACKAGES],
            check=True,
            capture_output=True,
            text=True,
        )

        assert completed.stdout.strip() == "[]"
