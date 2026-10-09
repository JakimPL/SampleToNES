from typing import List

import pytest

from sampletones.commands.registry import COMMANDS
from sampletones.commands.self_check import GPU_FLAG
from sampletones.dispatcher import dispatch

CHECK = "sampletones.self_check.run_self_check"


class TestSelfCheck:
    def test_the_status_is_the_checks_own(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(CHECK, lambda *, gpu: 7)

        assert dispatch(COMMANDS, ["self-check"]) == 7

    def test_the_gpu_flag_holds_the_build_to_the_gpu(self, monkeypatch: pytest.MonkeyPatch) -> None:
        held: List[bool] = []

        def run_self_check(*, gpu: bool) -> int:
            held.append(gpu)
            return 0

        monkeypatch.setattr(CHECK, run_self_check)

        assert dispatch(COMMANDS, ["self-check"]) == 0
        assert dispatch(COMMANDS, ["self-check", GPU_FLAG]) == 0
        assert held == [False, True]
