from pathlib import Path

import pytest

from sampletones_shared.documentation.site import DOCUMENTATION_DIRECTORY, INDEX_FILE, STAMP_FILE, DocumentationSite
from sampletones_shared.paths.package import package_directory
from sampletones_shared.paths.resources import ASSETS_PACKAGE


@pytest.fixture
def site(tmp_path: Path) -> DocumentationSite:
    (tmp_path / "guide").mkdir()
    (tmp_path / INDEX_FILE).write_text("<p>index</p>", encoding="utf-8")
    (tmp_path / "guide" / "page.html").write_text("<p>page</p>", encoding="utf-8")
    return DocumentationSite(tmp_path)


class TestDocumentationSite:
    def test_the_shipped_site_lies_in_the_assets_package(self) -> None:
        assert DocumentationSite.shipped().directory == package_directory(ASSETS_PACKAGE) / DOCUMENTATION_DIRECTORY

    def test_an_unsealed_site_reads_no_stamp(self, site: DocumentationSite) -> None:
        assert site.read_stamp() is None

    def test_the_written_stamp_is_the_one_its_files_earn(self, site: DocumentationSite) -> None:
        stamp = site.write_stamp()

        assert site.read_stamp() == stamp == site.content_stamp()
        assert (site.directory / STAMP_FILE).is_file()

    def test_a_changed_file_earns_another_stamp(self, site: DocumentationSite) -> None:
        stamp = site.write_stamp()
        (site.directory / "guide" / "page.html").write_text("<p>changed</p>", encoding="utf-8")

        assert site.content_stamp() != stamp

    def test_a_moved_file_earns_another_stamp(self, site: DocumentationSite) -> None:
        stamp = site.write_stamp()
        (site.directory / "guide" / "page.html").rename(site.directory / "page.html")

        assert site.content_stamp() != stamp

    def test_the_stamp_leaves_itself_out(self, site: DocumentationSite) -> None:
        before = site.content_stamp()
        site.write_stamp()

        assert site.content_stamp() == before
