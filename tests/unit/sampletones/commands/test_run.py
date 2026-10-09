from pathlib import Path

import pytest

from sampletones.commands.registry import COMMANDS
from sampletones.dispatcher import dispatch
from tests.suite.commands import RecordedApplication

LAUNCHER = "sampletones.run.run_application"


class TestRun:
    def test_no_arguments_start_the_application_with_the_saved_configuration(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        application = RecordedApplication()
        monkeypatch.setattr(LAUNCHER, application)

        assert dispatch(COMMANDS, []) == 0
        assert application.starts == [{"config": None, "library": None, "reconstruction": None, "project": None}]

    def test_a_configuration_reaches_the_application(self, monkeypatch: pytest.MonkeyPatch) -> None:
        application = RecordedApplication()
        monkeypatch.setattr(LAUNCHER, application)

        assert dispatch(COMMANDS, ["run", "--config", "custom.json"]) == 0
        assert application.starts[0]["config"] == Path("custom.json")
