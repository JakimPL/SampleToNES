from pathlib import Path
from typing import Final, List, Tuple

import pytest

from assets.icons.__main__ import main
from assets.icons.mark.specification import Mark
from assets.icons.paths import ICONS_DIRECTORY

WRITER: Final[str] = "assets.icons.__main__.write_icon_suite"


class RecordedSuite:
    def __init__(self) -> None:
        self.writes: List[Tuple[Path, Mark]] = []

    def __call__(self, directory: Path, mark: Mark) -> List[Path]:
        self.writes.append((directory, mark))
        return [directory / "sampletones.svg"]


class TestIcons:
    def test_without_a_directory_the_shipped_icons_are_written(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        suite = RecordedSuite()
        monkeypatch.setattr(WRITER, suite)

        assert main([]) == 0
        assert [directory for directory, _ in suite.writes] == [ICONS_DIRECTORY]
        assert suite.writes[0][1] == Mark.load()
        assert f"Wrote {ICONS_DIRECTORY / 'sampletones.svg'}" in capsys.readouterr().out

    def test_a_directory_of_its_own_is_written_where_it_says(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        suite = RecordedSuite()
        monkeypatch.setattr(WRITER, suite)

        assert main(["--output", str(tmp_path)]) == 0
        assert [directory for directory, _ in suite.writes] == [tmp_path]
