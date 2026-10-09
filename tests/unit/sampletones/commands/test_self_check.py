import pytest

from sampletones.commands.registry import COMMANDS
from sampletones.dispatcher import dispatch

CHECK = "sampletones.self_check.run_self_check"


class TestSelfCheck:
    def test_the_status_is_the_checks_own(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(CHECK, lambda: 7)

        assert dispatch(COMMANDS, ["self-check"]) == 7
