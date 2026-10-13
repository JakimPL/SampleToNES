from pathlib import Path
from typing import List

import pytest

from sampletones_shared.exceptions import FileNotOpenedError
from sampletones_shared.utils.system.opening.browser import BrowserFileOpener

WEBBROWSER = "sampletones_shared.utils.system.opening.browser.webbrowser.open"


class TestBrowserFileOpener:
    def test_the_file_is_handed_over_as_a_file_link(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        asked: List[str] = []
        monkeypatch.setattr(WEBBROWSER, lambda link: asked.append(link) or True)
        page = tmp_path / "index.html"

        BrowserFileOpener().open(page)

        assert asked == [page.resolve().as_uri()]

    def test_a_system_with_no_browser_is_reported(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(WEBBROWSER, lambda link: False)

        with pytest.raises(FileNotOpenedError):
            BrowserFileOpener().open(tmp_path / "index.html")
