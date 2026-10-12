import subprocess
from pathlib import Path
from typing import Any, Dict, Final, List

import pytest

from sampletones_shared.utils.system.opening.xdg_open import XDG_OPEN, XdgOpenFileOpener

POPEN: Final[str] = "sampletones_shared.utils.system.opening.xdg_open.subprocess.Popen"
PROGRAM_ENVIRONMENT: Final[str] = "sampletones_shared.utils.system.opening.xdg_open.program_environment"
ENVIRONMENT: Final[Dict[str, str]] = {"HOME": "/home/reader"}


class RecordedPopen:
    def __init__(self) -> None:
        self.calls: List[Dict[str, Any]] = []

    def __call__(self, command: List[str], **options: Any) -> None:
        self.calls.append({"command": command, **options})


class TestXdgOpenFileOpener:
    def test_the_file_is_handed_to_a_detached_xdg_open(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        popen = RecordedPopen()
        monkeypatch.setattr(POPEN, popen)
        monkeypatch.setattr(PROGRAM_ENVIRONMENT, lambda: ENVIRONMENT)
        page = tmp_path / "index.html"

        XdgOpenFileOpener().open(page)

        [call] = popen.calls
        assert call["command"] == [XDG_OPEN, str(page)]
        assert call["start_new_session"] is True
        assert call["env"] == ENVIRONMENT
        assert call["stdout"] is subprocess.DEVNULL

    def test_a_missing_program_reaches_the_caller(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        def missing(command: List[str], **options: Any) -> None:
            raise FileNotFoundError(command[0])

        monkeypatch.setattr(POPEN, missing)

        with pytest.raises(OSError):
            XdgOpenFileOpener().open(tmp_path / "index.html")
