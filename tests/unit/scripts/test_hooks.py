from pathlib import Path

from tests.suite.bootstrap import RecordingRunner
from tests.suite.scripts import load_script

hooks = load_script("hooks.py")


class TestInstallHooks:
    def test_both_hook_stages_are_installed_from_the_repository(self, tmp_path: Path) -> None:
        runner = RecordingRunner({}, None)

        hooks.install_hooks(tmp_path, runner=runner, environment={})

        assert runner.lines == [" ".join(hooks.INSTALL_HOOKS)]
        assert "--hook-type pre-commit --hook-type pre-push" in runner.lines[0]
        assert runner.commands[0].cwd == tmp_path
