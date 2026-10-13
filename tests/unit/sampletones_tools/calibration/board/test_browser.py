from pathlib import Path
from typing import List

import pytest

from sampletones_shared.exceptions import FileNotOpenedError
from sampletones_tools.calibration.board.browser import open_page

SELECT_OPENER = "sampletones_tools.calibration.board.browser.select_file_opener"


class RecordedOpener:
    def __init__(self, *, takes: bool) -> None:
        self.opened: List[Path] = []
        self._takes = takes

    def open(self, path: Path) -> None:
        self.opened.append(path)
        if not self._takes:
            raise FileNotOpenedError(f"No browser took {path}")


@pytest.fixture
def page(tmp_path: Path) -> Path:
    path = tmp_path / "index.html"
    path.write_text("", encoding="utf-8")
    return path


class TestOpenPage:
    def test_the_page_is_handed_to_the_system_opener(self, page: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        opener = RecordedOpener(takes=True)
        monkeypatch.setattr(SELECT_OPENER, lambda: opener)

        assert open_page(page)
        assert opener.opened == [page.resolve()]

    def test_a_system_with_no_browser_leaves_the_link_alone(self, page: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        opener = RecordedOpener(takes=False)
        monkeypatch.setattr(SELECT_OPENER, lambda: opener)

        assert not open_page(page)
