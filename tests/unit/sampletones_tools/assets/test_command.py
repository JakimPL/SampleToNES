from pathlib import Path
from typing import Final, List, Tuple

import pytest

from sampletones.commands.registry import COMMANDS
from sampletones.dispatcher import dispatch
from sampletones_tools.assets.mark.specification import Mark
from sampletones_tools.assets.paths import ICONS_DIRECTORY

WRITER: Final[str] = "sampletones_tools.assets.mark.suite.write_icon_suite"
GUARD: Final[str] = "sampletones_tools.checkout.require_checkout"


class RecordedSuite:
    def __init__(self) -> None:
        self.writes: List[Tuple[Path, Mark]] = []

    def __call__(self, directory: Path, mark: Mark) -> List[Path]:
        self.writes.append((directory, mark))
        return [directory / "sampletones.svg"]


class TestIcons:
    def test_without_a_directory_the_shipped_icons_are_written_from_a_checkout(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        suite = RecordedSuite()
        guarded: List[str] = []
        monkeypatch.setattr(WRITER, suite)
        monkeypatch.setattr(GUARD, guarded.append)

        assert dispatch(COMMANDS, ["icons"]) == 0
        assert [directory for directory, _ in suite.writes] == [ICONS_DIRECTORY]
        assert suite.writes[0][1] == Mark.load()
        assert guarded == ["icons"]
        assert f"Wrote {ICONS_DIRECTORY / 'sampletones.svg'}" in capsys.readouterr().out

    def test_a_directory_of_its_own_is_written_from_a_checkout_too(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        suite = RecordedSuite()
        guarded: List[str] = []
        monkeypatch.setattr(WRITER, suite)
        monkeypatch.setattr(GUARD, guarded.append)

        assert dispatch(COMMANDS, ["icons", "--directory", str(tmp_path)]) == 0
        assert [directory for directory, _ in suite.writes] == [tmp_path]
        assert guarded == ["icons"]
