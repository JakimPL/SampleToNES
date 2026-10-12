from pathlib import Path

import pytest

from sampletones_application.logic.documentation.shelf import STAGING_PREFIX, STAGING_SUFFIX, DocumentationShelf
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
def copies(tmp_path: Path) -> Path:
    return tmp_path / "copies"


@pytest.fixture
def shelf(site: DocumentationSite, copies: Path) -> DocumentationShelf:
    return DocumentationShelf(site=site, copies=copies)


def stamp_of(site: DocumentationSite) -> str:
    stamp = site.read_stamp()
    assert stamp is not None
    return stamp


class TestPlace:
    def test_the_pages_are_copied_under_their_stamp(
        self,
        shelf: DocumentationShelf,
        site: DocumentationSite,
        copies: Path,
    ) -> None:
        index = shelf.place()

        assert index == copies / stamp_of(site) / INDEX_FILE
        assert (index.parent / "guide" / "page.html").read_text(encoding="utf-8") == "<p>page</p>"
        assert DocumentationSite(index.parent).read_stamp() == stamp_of(site)

    def test_a_copy_in_place_is_read_again(self, shelf: DocumentationShelf) -> None:
        index = shelf.place()
        marker = index.parent / "opened.txt"
        marker.write_text("kept", encoding="utf-8")

        assert shelf.place() == index
        assert marker.is_file()

    def test_an_unfinished_copy_is_made_again(
        self, shelf: DocumentationShelf, site: DocumentationSite, copies: Path
    ) -> None:
        unfinished = copies / stamp_of(site)
        unfinished.mkdir(parents=True)
        (unfinished / "half.html").write_text("half", encoding="utf-8")

        index = shelf.place()

        assert index.is_file()
        assert not (unfinished / "half.html").exists()

    def test_a_stale_staging_folder_gives_way(
        self, shelf: DocumentationShelf, site: DocumentationSite, copies: Path
    ) -> None:
        staging = copies / f"{STAGING_PREFIX}{stamp_of(site)}{STAGING_SUFFIX}"
        staging.mkdir(parents=True)
        (staging / "left.html").write_text("left", encoding="utf-8")

        index = shelf.place()

        assert not staging.exists()
        assert not (index.parent / "left.html").exists()

    def test_copies_of_other_versions_are_let_go(self, shelf: DocumentationShelf, copies: Path) -> None:
        older = copies / "0123456789abcdef"
        older.mkdir(parents=True)

        index = shelf.place()

        assert sorted(path.name for path in copies.iterdir()) == [index.parent.name]


class TestPlaceRefuses:
    def test_an_installation_without_pages(self, tmp_path: Path, copies: Path) -> None:
        shelf = DocumentationShelf(site=DocumentationSite(tmp_path / "missing"), copies=copies)

        with pytest.raises(DocumentationUnavailableError):
            shelf.place()

    def test_an_unsealed_site(self, site: DocumentationSite, copies: Path) -> None:
        site.stamp_path.unlink()

        with pytest.raises(DocumentationUnavailableError):
            DocumentationShelf(site=site, copies=copies).place()

    def test_a_site_without_an_index(self, site: DocumentationSite, copies: Path) -> None:
        site.index.unlink()

        with pytest.raises(DocumentationUnavailableError):
            DocumentationShelf(site=site, copies=copies).place()
