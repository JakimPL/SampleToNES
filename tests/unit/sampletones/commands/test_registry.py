from sampletones.commands.registry import COMMANDS, USER_COMMANDS
from sampletones.dispatcher import DEFAULT_COMMAND, build_parser


class TestRegistry:
    def test_the_user_commands_are_the_ones_the_guide_names(self) -> None:
        assert [command.name for command in USER_COMMANDS] == ["run", "open", "convert", "library", "self-check"]

    def test_the_default_command_is_registered(self) -> None:
        assert DEFAULT_COMMAND in {command.name for command in COMMANDS}

    def test_the_registry_builds_one_parser(self) -> None:
        assert build_parser(COMMANDS).format_help()
