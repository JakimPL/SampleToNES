import subprocess
from pathlib import Path

import pytest

from automation.boundaries.reveals import FILE_MANAGER, FileManagerStandIn


@pytest.fixture
def stand_in(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FileManagerStandIn:
    file_manager = FileManagerStandIn(tmp_path / "programs", tmp_path / "shown.log", tmp_path / "opened.log")
    file_manager.install(monkeypatch)
    return file_manager


@pytest.fixture
def page(tmp_path: Path) -> Path:
    path = tmp_path / "index.html"
    path.write_text("", encoding="utf-8")
    return path


class TestFileManagerStandIn:
    def test_nothing_is_noted_before_a_program_runs(self, stand_in: FileManagerStandIn) -> None:
        assert stand_in.shown() == ()
        assert stand_in.opened() == ()

    def test_xdg_open_on_a_folder_shows_it(self, stand_in: FileManagerStandIn, tmp_path: Path) -> None:
        subprocess.run(["xdg-open", str(tmp_path)], check=True)

        assert stand_in.shown() == (tmp_path,)
        assert stand_in.opened() == ()

    def test_xdg_open_on_a_file_opens_it(self, stand_in: FileManagerStandIn, page: Path) -> None:
        subprocess.run(["xdg-open", str(page)], check=True)

        assert stand_in.opened() == (page,)
        assert stand_in.shown() == ()

    def test_the_file_manager_shows_what_it_is_given(self, stand_in: FileManagerStandIn, page: Path) -> None:
        subprocess.run([FILE_MANAGER, str(page)], check=True)

        assert stand_in.shown() == (page,)
