import pytest

from tests.suite.bootstrap import RecordingRunner
from tests.suite.scripts import load_script

hooks = load_script("hooks.py")


class TestMain:
    def test_both_hook_stages_are_installed(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        runner = RecordingRunner({}, None)
        monkeypatch.setattr(hooks, "run", runner)

        assert hooks.main([]) == 0
        assert runner.lines == ["uv run pre-commit install --hook-type pre-commit --hook-type pre-push"]
        assert "Pre-commit hooks installed." in capsys.readouterr().out
