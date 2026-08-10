from pathlib import Path
from typing import Dict, Final, List, Optional

import yaml

from sampletones_shared.paths import REPOSITORY_ROOT

PRE_COMMIT_CONFIG: Final[Path] = REPOSITORY_ROOT / ".pre-commit-config.yaml"
MAKEFILE: Final[Path] = REPOSITORY_ROOT / "Makefile"

FILE_ENCODING: Final[str] = "utf-8"
LOCAL_REPOSITORY: Final[str] = "local"
CHECK_SCRIPTS: Final[str] = "scripts/checks/"
TARGET_PREFIX: Final[str] = "check-"
SCRIPT_SUFFIX: Final[str] = ".py"
RECIPE_PREFIX: Final[str] = "\t"
TARGET_SUFFIX: Final[str] = ":"


def check_hooks() -> List[Dict[str, object]]:
    """Every local hook running one of the check scripts, as the configuration declares it."""
    config = yaml.safe_load(PRE_COMMIT_CONFIG.read_text(encoding=FILE_ENCODING))
    return [
        hook
        for repository in config["repos"]
        if repository["repo"] == LOCAL_REPOSITORY
        for hook in repository["hooks"]
        if CHECK_SCRIPTS in str(hook["entry"])
    ]


def check_targets() -> Dict[str, str]:
    """The command each `check-*` target of the Makefile runs, keyed by target name."""
    targets: Dict[str, str] = {}
    target: Optional[str] = None
    for line in MAKEFILE.read_text(encoding=FILE_ENCODING).splitlines():
        if line.startswith(TARGET_PREFIX) and line.endswith(TARGET_SUFFIX):
            target = line.removesuffix(TARGET_SUFFIX)
        elif target is not None and line.startswith(RECIPE_PREFIX):
            targets[target] = line.strip()
            target = None

    return targets


def script_path(entry: str) -> Path:
    """The check script an entry runs, taken from the words the entry is written with."""
    return REPOSITORY_ROOT / next(word for word in entry.split() if word.endswith(SCRIPT_SUFFIX))


class TestCheckHooks:
    def test_the_configuration_declares_a_hook_for_every_check_script(self) -> None:
        scripts = {path.name for path in (REPOSITORY_ROOT / CHECK_SCRIPTS).glob(f"*{SCRIPT_SUFFIX}")}

        assert {script_path(str(hook["entry"])).name for hook in check_hooks()} == scripts

    def test_every_check_hook_names_a_script_that_is_there(self) -> None:
        assert all(script_path(str(hook["entry"])).is_file() for hook in check_hooks())

    def test_every_check_hook_sweeps_the_whole_tree(self) -> None:
        """A hook handed the staged files checks the staged subset, which passes what it never reads."""
        assert all(hook["pass_filenames"] is False for hook in check_hooks())


class TestCheckTargets:
    def test_each_hook_and_its_make_target_run_the_same_command(self) -> None:
        commands = {f"{TARGET_PREFIX}{hook['id']}": str(hook["entry"]) for hook in check_hooks()}

        assert check_targets() == commands
