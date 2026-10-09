import subprocess
from typing import List, Sequence

import pytest

from sampletones_tools.codec.study.report import run
from sampletones_tools.codec.study.report.run import UNKNOWN_COMMIT, commit_hash


class TestCommitHash:
    def test_a_copy_outside_a_checkout_records_unknown_without_asking_git(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        asked: List[Sequence[str]] = []
        monkeypatch.setattr(run, "is_checkout", lambda root: False)
        monkeypatch.setattr(run.subprocess, "run", lambda command, **options: asked.append(command))

        assert commit_hash() == UNKNOWN_COMMIT
        assert asked == []

    def test_a_machine_without_git_records_unknown(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def missing_git(command: Sequence[str], **options: object) -> subprocess.CompletedProcess[str]:
            raise FileNotFoundError(command[0])

        monkeypatch.setattr(run, "is_checkout", lambda root: True)
        monkeypatch.setattr(run.subprocess, "run", missing_git)

        assert commit_hash() == UNKNOWN_COMMIT

    def test_a_checkout_records_what_git_reports(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def reporting_git(command: Sequence[str], **options: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(command, 0, stdout="abc1234\n", stderr="")

        monkeypatch.setattr(run, "is_checkout", lambda root: True)
        monkeypatch.setattr(run.subprocess, "run", reporting_git)

        assert commit_hash() == "abc1234"
