from pathlib import Path
from typing import List

import pytest

from sampletones_application.ui.elements import path as path_module
from sampletones_application.ui.elements.path import GUIDestinationPathText, GUIPathText

FILENAME = "chiptune.wav"


def _path_text(path: Path) -> GUIPathText:
    """A path text carrying only the path a click reads, bypassing the DearPyGui-dependent
    constructor."""
    instance = GUIPathText.__new__(GUIPathText)
    instance.path = path
    return instance


def _destination_text(path: Path) -> GUIDestinationPathText:
    instance = GUIDestinationPathText.__new__(GUIDestinationPathText)
    instance.path = path
    return instance


@pytest.fixture
def opened(monkeypatch: pytest.MonkeyPatch) -> List[Path]:
    revealed: List[Path] = []
    monkeypatch.setattr(path_module, "open_path_in_explorer", revealed.append)
    return revealed


class TestAPathThatStands:
    """A path text shows what it points at, so a click reaches the file itself."""

    def test_an_existing_file_is_revealed(self, tmp_path: Path, opened: List[Path]) -> None:
        filepath = tmp_path / FILENAME
        filepath.touch()

        _path_text(filepath)._on_clicked()

        assert opened == [filepath]

    def test_a_file_yet_to_be_written_reveals_nothing(
        self,
        tmp_path: Path,
        opened: List[Path],
    ) -> None:
        _path_text(tmp_path / FILENAME)._on_clicked()

        assert not opened


class TestADestination:
    """A destination names what an operation will leave behind, so a click reaches the nearest place
    that stands however far the operation has got."""

    def test_the_directory_a_file_is_written_into_is_revealed(
        self,
        tmp_path: Path,
        opened: List[Path],
    ) -> None:
        _destination_text(tmp_path / FILENAME)._on_clicked()

        assert opened == [tmp_path]

    def test_a_written_file_is_revealed_itself(
        self,
        tmp_path: Path,
        opened: List[Path],
    ) -> None:
        filepath = tmp_path / FILENAME
        filepath.touch()

        _destination_text(filepath)._on_clicked()

        assert opened == [filepath]

    def test_a_written_directory_is_revealed_itself(
        self,
        tmp_path: Path,
        opened: List[Path],
    ) -> None:
        directory = tmp_path / "renders"
        directory.mkdir()

        _destination_text(directory)._on_clicked()

        assert opened == [directory]

    def test_a_directory_yet_to_be_created_falls_back_to_the_one_holding_it(
        self,
        tmp_path: Path,
        opened: List[Path],
    ) -> None:
        _destination_text(tmp_path / "renders" / "session" / FILENAME)._on_clicked()

        assert opened == [tmp_path]

    def test_an_empty_path_reveals_nothing(self, opened: List[Path]) -> None:
        _destination_text(Path())._on_clicked()

        assert not opened
