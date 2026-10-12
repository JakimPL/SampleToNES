from pathlib import Path

import pytest

from sampletones_application.logic.documentation.shelf import (
    HIDDEN_PREFIX,
    RETIRED_SUFFIX,
    STAGING_SUFFIX,
    DocumentationShelf,
)
from sampletones_shared.documentation.site import INDEX_FILE, DocumentationSite
from sampletones_shared.exceptions import DocumentationUnavailableError


@pytest.fixture
def site(tmp_path: Path) -> DocumentationSite:
    shipped = DocumentationSite(tmp_path / "shipped")
    (shipped.directory / "guide").mkdir(parents=True)
    shipped.index.write_text("<p>index</p>", encoding="utf-8")
    (shipped.directory / "guide" / "page.html").write_text("<p>page</p>", encoding="utf-8")
    shipped.write_stamp()
    return shipped


@pytest.fixture
def directory(tmp_path: Path) -> Path:
    return tmp_path / "data" / "documentation"


@pytest.fixture
def shelf(site: DocumentationSite, directory: Path) -> DocumentationShelf:
    return DocumentationShelf(site=site, directory=directory)


def beside(directory: Path, suffix: str) -> Path:
    return directory.with_name(f"{HIDDEN_PREFIX}{directory.name}{suffix}")


class TestPlace:
    def test_the_pages_are_copied_into_the_folder(
        self,
        shelf: DocumentationShelf,
        site: DocumentationSite,
        directory: Path,
    ) -> None:
        index = shelf.place()

        assert index == directory / INDEX_FILE
        assert (directory / "guide" / "page.html").read_text(encoding="utf-8") == "<p>page</p>"
        assert DocumentationSite(directory).read_stamp() == site.read_stamp()

    def test_a_copy_of_the_same_pages_is_read_again(self, shelf: DocumentationShelf, directory: Path) -> None:
        shelf.place()
        marker = directory / "opened.txt"
        marker.write_text("kept", encoding="utf-8")

        assert shelf.place() == directory / INDEX_FILE
        assert marker.is_file()

    def test_new_pages_replace_the_copy_whole(
        self,
        shelf: DocumentationShelf,
        site: DocumentationSite,
        directory: Path,
    ) -> None:
        shelf.place()
        (directory / "opened.txt").write_text("from the earlier pages", encoding="utf-8")
        site.index.write_text("<p>new index</p>", encoding="utf-8")
        site.write_stamp()

        index = shelf.place()

        assert index.read_text(encoding="utf-8") == "<p>new index</p>"
        assert not (directory / "opened.txt").exists()
        assert DocumentationSite(directory).read_stamp() == site.read_stamp()

    def test_a_copy_in_an_earlier_layout_is_replaced(self, shelf: DocumentationShelf, directory: Path) -> None:
        earlier = directory / "0123456789abcdef"
        earlier.mkdir(parents=True)
        (earlier / INDEX_FILE).write_text("<p>earlier</p>", encoding="utf-8")

        index = shelf.place()

        assert index.read_text(encoding="utf-8") == "<p>index</p>"
        assert not earlier.exists()

    @pytest.mark.parametrize("suffix", [STAGING_SUFFIX, RETIRED_SUFFIX], ids=["staging", "retired"])
    def test_a_folder_an_interrupted_replacement_left_gives_way(
        self,
        shelf: DocumentationShelf,
        directory: Path,
        suffix: str,
    ) -> None:
        leftover = beside(directory, suffix)
        leftover.mkdir(parents=True)
        (leftover / "left.html").write_text("left", encoding="utf-8")

        index = shelf.place()

        assert sorted(path.name for path in directory.parent.iterdir()) == [directory.name]
        assert not (index.parent / "left.html").exists()


class TestPlaceRefuses:
    def test_an_installation_without_pages(self, tmp_path: Path, directory: Path) -> None:
        shelf = DocumentationShelf(site=DocumentationSite(tmp_path / "missing"), directory=directory)

        with pytest.raises(DocumentationUnavailableError):
            shelf.place()

    def test_an_unsealed_site(self, site: DocumentationSite, directory: Path) -> None:
        site.stamp_path.unlink()

        with pytest.raises(DocumentationUnavailableError):
            DocumentationShelf(site=site, directory=directory).place()

    def test_a_site_without_an_index(self, site: DocumentationSite, directory: Path) -> None:
        site.index.unlink()

        with pytest.raises(DocumentationUnavailableError):
            DocumentationShelf(site=site, directory=directory).place()

    def test_a_folder_that_cannot_be_written(self, site: DocumentationSite, tmp_path: Path) -> None:
        blocked = tmp_path / "blocked"
        blocked.write_text("a file where the folder belongs", encoding="utf-8")

        with pytest.raises(OSError):
            DocumentationShelf(site=site, directory=blocked / "documentation").place()
