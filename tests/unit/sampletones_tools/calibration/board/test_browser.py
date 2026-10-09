from pathlib import Path
from typing import List

import pytest

from sampletones_tools.calibration.board.browser import open_page

WEBBROWSER = "sampletones_tools.calibration.board.browser.webbrowser.open"


class TestOpenPage:
    def test_the_page_is_handed_over_as_a_file_link(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        asked: List[str] = []
        monkeypatch.setattr(WEBBROWSER, lambda link: asked.append(link) or True)
        page = tmp_path / "index.html"
        page.write_text("", encoding="utf-8")

        assert open_page(page)
        assert asked == [page.resolve().as_uri()]

    def test_a_system_with_no_browser_leaves_the_link_alone(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(WEBBROWSER, lambda link: False)
        page = tmp_path / "index.html"
        page.write_text("", encoding="utf-8")

        assert not open_page(page)
