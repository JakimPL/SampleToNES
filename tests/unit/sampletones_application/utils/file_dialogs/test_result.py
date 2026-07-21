from pathlib import Path
from typing import List, Optional, Tuple

from sampletones_application.utils.file_dialogs.result import ignore_none_path


class Recorder:
    def __init__(self) -> None:
        self.calls: List[Path] = []

    @ignore_none_path
    def handle(self, filepath: Path) -> None:
        self.calls.append(filepath)


class ArgRecorder:
    def __init__(self) -> None:
        self.seen: Optional[Tuple[Path, str]] = None

    @ignore_none_path
    def handle(self, filepath: Path, extra: str) -> None:
        self.seen = (filepath, extra)


class ReturningRecorder:
    def __init__(self) -> None:
        self.calls: List[Path] = []

    @ignore_none_path(default=False)
    def handle(self, filepath: Path) -> bool:
        self.calls.append(filepath)
        return True


def test_runs_with_path() -> None:
    recorder = Recorder()
    recorder.handle(Path("/a/b"))
    assert recorder.calls == [Path("/a/b")]


def test_skips_none() -> None:
    recorder = Recorder()
    recorder.handle(None)
    assert recorder.calls == []


def test_forwards_extra_arguments() -> None:
    recorder = ArgRecorder()
    recorder.handle(Path("/a/b"), "extra")
    assert recorder.seen == (Path("/a/b"), "extra")


def test_returns_wrapped_result_with_path() -> None:
    recorder = ReturningRecorder()
    assert recorder.handle(Path("/a/b")) is True
    assert recorder.calls == [Path("/a/b")]


def test_returns_default_on_none() -> None:
    recorder = ReturningRecorder()
    assert recorder.handle(None) is False
    assert recorder.calls == []
