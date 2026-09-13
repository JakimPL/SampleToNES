from sampletones.commands.registry import USER_COMMANDS
from sampletones_tools.registry import DEVELOPER_COMMANDS


class TestDeveloperCommands:
    def test_every_developer_command_has_a_name_of_its_own(self) -> None:
        names = [command.name for command in DEVELOPER_COMMANDS]

        assert len(set(names)) == len(names)
        assert not set(names) & {command.name for command in USER_COMMANDS}
