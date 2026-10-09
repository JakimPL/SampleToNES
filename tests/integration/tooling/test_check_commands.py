from pathlib import Path
from typing import Dict, Final, List

import yaml

from sampletones.commands.registry import COMMANDS
from sampletones.dispatcher import build_parser
from sampletones_shared.paths.source import REPOSITORY_ROOT
from sampletones_tools.checks.registry import GATES

PRE_COMMIT_CONFIG: Final[Path] = REPOSITORY_ROOT / ".pre-commit-config.yaml"

FILE_ENCODING: Final[str] = "utf-8"
LOCAL_REPOSITORY: Final[str] = "local"
ENTRY_PREFIX: Final[str] = "uv run sampletones "
CHECK_PREFIX: Final[str] = f"{ENTRY_PREFIX}check "


def check_hooks() -> List[Dict[str, object]]:
    """Every local hook running one of the checks, as the configuration declares it."""
    config = yaml.safe_load(PRE_COMMIT_CONFIG.read_text(encoding=FILE_ENCODING))
    return [
        hook
        for repository in config["repos"]
        if repository["repo"] == LOCAL_REPOSITORY
        for hook in repository["hooks"]
        if str(hook["entry"]).startswith(CHECK_PREFIX)
    ]


def hook_gate(hook: Dict[str, object]) -> str:
    """The check a hook runs, taken from the words the entry is written with."""
    return str(hook["entry"]).removeprefix(CHECK_PREFIX).split()[0]


class TestCheckHooks:
    def test_the_configuration_declares_a_hook_for_every_check(self) -> None:
        hooks = check_hooks()

        assert GATES
        assert {hook_gate(hook) for hook in hooks} == {gate.name for gate in GATES}
        assert len(hooks) == len(GATES)

    def test_every_check_hook_parses_as_the_entry_runs_it(self) -> None:
        """A hook's entry is a command line the entry accepts, so a renamed option fails here."""
        parser = build_parser(COMMANDS)

        for hook in check_hooks():
            parser.parse_args(str(hook["entry"]).removeprefix(ENTRY_PREFIX).split())

    def test_every_check_hook_sweeps_the_whole_tree(self) -> None:
        """A hook handed the staged files checks the staged subset, which passes what it never reads."""
        assert all(hook["pass_filenames"] is False for hook in check_hooks())
