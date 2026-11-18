from pathlib import Path
from typing import Final, List, Tuple

import pytest

from sampletones.commands.registry import COMMANDS
from sampletones.dispatcher import dispatch
from sampletones_tools.player.assembler.layout import ASSEMBLY_DIRECTORY, INCLUDE_DIRECTORY, SOURCE_DIRECTORY
from sampletones_tools.player.graphics.paths import PATTERNS_DIRECTORY

BUILDER: Final[str] = "sampletones_tools.player.graphics.builder.build_patterns"
DATA_BUILDER: Final[str] = "sampletones_tools.player.graphics.builder.build_shell_data"
PREVIEWS: Final[str] = "sampletones_tools.player.graphics.preview.write_previews"
GUARD: Final[str] = "sampletones_tools.checkout.require_checkout"
PATTERNS: Final[bytes] = bytes(7)
PICTURE_NAME: Final[str] = "deck.png"


class RecordedBuild:
    def __init__(self) -> None:
        self.destinations: List[Path] = []

    def __call__(self, destination: Path) -> bytes:
        self.destinations.append(destination)
        return PATTERNS


class RecordedPreviews:
    def __init__(self) -> None:
        self.directories: List[Path] = []

    def __call__(self, directory: Path) -> List[Path]:
        self.directories.append(directory)
        return [directory / PICTURE_NAME]


class RecordedData:
    def __init__(self) -> None:
        self.directories: List[Tuple[Path, Path]] = []

    def __call__(self, include_directory: Path, source_directory: Path) -> None:
        self.directories.append((include_directory, source_directory))


def _refuse(command: str) -> None:
    raise AssertionError(f"the checkout guard ran for {command}")


class TestTiles:
    def test_without_a_directory_the_shipped_tables_are_written_from_a_checkout(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        build = RecordedBuild()
        data = RecordedData()
        guarded: List[str] = []
        monkeypatch.setattr(BUILDER, build)
        monkeypatch.setattr(DATA_BUILDER, data)
        monkeypatch.setattr(GUARD, guarded.append)

        assert dispatch(COMMANDS, ["tiles"]) == 0
        assert build.destinations == [PATTERNS_DIRECTORY]
        assert data.directories == [(ASSEMBLY_DIRECTORY / INCLUDE_DIRECTORY, ASSEMBLY_DIRECTORY / SOURCE_DIRECTORY)]
        assert guarded == ["tiles"]
        assert "patterns.bin  7 bytes" in capsys.readouterr().out

    def test_a_directory_of_its_own_needs_no_checkout(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        build = RecordedBuild()
        data = RecordedData()
        monkeypatch.setattr(BUILDER, build)
        monkeypatch.setattr(DATA_BUILDER, data)
        monkeypatch.setattr(GUARD, _refuse)

        assert dispatch(COMMANDS, ["tiles", "--output", str(tmp_path)]) == 0
        assert build.destinations == [tmp_path]
        assert data.directories == [(tmp_path, tmp_path)]

    def test_pictures_are_written_where_asked_and_named(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        tmp_path: Path,
    ) -> None:
        previews = RecordedPreviews()
        monkeypatch.setattr(BUILDER, RecordedBuild())
        monkeypatch.setattr(DATA_BUILDER, RecordedData())
        monkeypatch.setattr(PREVIEWS, previews)
        pictures = tmp_path / "pictures"

        assert dispatch(COMMANDS, ["tiles", "--output", str(tmp_path), "--preview", str(pictures)]) == 0
        assert previews.directories == [pictures]
        assert str(pictures / PICTURE_NAME) in capsys.readouterr().out

    def test_without_a_preview_directory_no_picture_is_written(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        previews = RecordedPreviews()
        monkeypatch.setattr(BUILDER, RecordedBuild())
        monkeypatch.setattr(DATA_BUILDER, RecordedData())
        monkeypatch.setattr(PREVIEWS, previews)

        assert dispatch(COMMANDS, ["tiles", "--output", str(tmp_path)]) == 0
        assert previews.directories == []
