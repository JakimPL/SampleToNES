from pathlib import Path
from typing import Final, List
from unittest.mock import MagicMock

import pytest

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.coordinators.documentation import DocumentationCoordinator
from sampletones_application.logic.documentation.shelf import DocumentationShelf
from sampletones_application.paths import LANG_EN
from sampletones_application.tags.general import TAG_GLOBAL_DIALOG_DOCUMENTATION
from sampletones_shared.documentation.site import INDEX_FILE, DocumentationSite
from sampletones_shared.exceptions import FileNotOpenedError

LANGUAGE_MANAGER: Final[LanguageManager] = LanguageManager(LANG_EN)
ADDRESS: Final[str] = "https://example.com/docs"


class RecordedOpener:
    def __init__(self, *, takes: bool) -> None:
        self.opened: List[Path] = []
        self._takes = takes

    def open(self, path: Path) -> None:
        self.opened.append(path)
        if not self._takes:
            raise FileNotOpenedError(f"No browser took {path}")


@pytest.fixture
def dialogs() -> MagicMock:
    return MagicMock()


@pytest.fixture
def shipped(tmp_path: Path) -> DocumentationSite:
    site = DocumentationSite(tmp_path / "shipped")
    site.directory.mkdir()
    site.index.write_text("<p>index</p>", encoding="utf-8")
    site.write_stamp()
    return site


def coordinator(
    site: DocumentationSite,
    copies: Path,
    opener: RecordedOpener,
    dialogs: MagicMock,
) -> DocumentationCoordinator:
    return DocumentationCoordinator(
        shelf=DocumentationShelf(site=site, copies=copies),
        opener=opener,
        dialogs=dialogs,
        language_manager=LANGUAGE_MANAGER,
        address=ADDRESS,
    )


class TestOpenDocumentation:
    def test_the_copied_index_is_opened(self, shipped: DocumentationSite, tmp_path: Path, dialogs: MagicMock) -> None:
        opener = RecordedOpener(takes=True)

        coordinator(shipped, tmp_path / "copies", opener, dialogs).open()

        assert opener.opened == [tmp_path / "copies" / str(shipped.read_stamp()) / INDEX_FILE]
        dialogs.show_info.assert_not_called()
        dialogs.show_error.assert_not_called()

    def test_an_installation_without_pages_names_the_online_copy(self, tmp_path: Path, dialogs: MagicMock) -> None:
        opener = RecordedOpener(takes=True)

        coordinator(DocumentationSite(tmp_path / "missing"), tmp_path / "copies", opener, dialogs).open()

        assert opener.opened == []
        dialogs.show_info.assert_called_once_with(
            TAG_GLOBAL_DIALOG_DOCUMENTATION,
            LANGUAGE_MANAGER["global.dialog.template.documentation_unavailable"].format(address=ADDRESS),
            LANGUAGE_MANAGER["global.dialog.title.documentation"],
            modal=True,
        )
        assert ADDRESS in dialogs.show_info.call_args.args[1]

    def test_a_browser_that_takes_nothing_is_reported(
        self,
        shipped: DocumentationSite,
        tmp_path: Path,
        dialogs: MagicMock,
    ) -> None:
        coordinator(shipped, tmp_path / "copies", RecordedOpener(takes=False), dialogs).open()

        [exception, message] = dialogs.show_error.call_args.args
        assert isinstance(exception, FileNotOpenedError)
        assert message == LANGUAGE_MANAGER["global.dialog.message.documentation_not_opened"]
        dialogs.show_info.assert_not_called()

    def test_a_copy_that_cannot_be_written_is_reported(
        self,
        shipped: DocumentationSite,
        tmp_path: Path,
        dialogs: MagicMock,
    ) -> None:
        blocked = tmp_path / "copies"
        blocked.write_text("a file where the folder belongs", encoding="utf-8")
        opener = RecordedOpener(takes=True)

        coordinator(shipped, blocked, opener, dialogs).open()

        assert opener.opened == []
        assert isinstance(dialogs.show_error.call_args.args[0], OSError)
