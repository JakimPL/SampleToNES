from pathlib import Path
from typing import List

import pytest

from assets.documentation.build import DOCUMENTATION_STYLESHEET, OutputOccupiedError, SiteRequest, build_site
from assets.documentation.links.resolver import BrokenLinkError
from assets.documentation.rendering.page import LAYOUT_DIRECTORY
from sampletones_shared.documentation.site import DocumentationSite
from tests.unit.assets.documentation.conftest import ADDRESS, VERSION


@pytest.fixture
def request_for(docs: Path, project: Path, tmp_path: Path) -> SiteRequest:
    return SiteRequest(docs=docs, project=project, output=tmp_path / "site")


@pytest.fixture
def site(request_for: SiteRequest) -> DocumentationSite:
    return build_site(request_for)


def written(site: DocumentationSite) -> List[str]:
    return sorted(path.relative_to(site.directory).as_posix() for path in site.directory.rglob("*") if path.is_file())


class TestBuildSite:
    def test_every_published_document_becomes_a_page(self, site: DocumentationSite) -> None:
        pages = [name for name in written(site) if name.endswith(".html")]

        assert pages == ["glossary.html", "guide/next.html", "guide/start.html", "index.html"]

    def test_only_the_pictures_a_page_shows_are_copied(self, site: DocumentationSite) -> None:
        assert [name for name in written(site) if name.startswith("images/")] == ["images/picture.webp"]
        assert (site.directory / "images" / "picture.webp").read_bytes() == b"picture"

    def test_the_layout_lies_beside_the_pages(self, site: DocumentationSite) -> None:
        assert (site.directory / LAYOUT_DIRECTORY / DOCUMENTATION_STYLESHEET).is_file()
        assert (site.directory / LAYOUT_DIRECTORY / "roles.css").is_file()

    def test_the_site_is_sealed_by_its_stamp(self, site: DocumentationSite) -> None:
        assert site.read_stamp() == site.content_stamp()

    def test_links_lead_to_pages_and_online_copies(self, site: DocumentationSite) -> None:
        start = (site.directory / "guide" / "start.html").read_text(encoding="utf-8")

        assert 'href="next.html#second-part"' in start
        assert f'href="{ADDRESS}/development/notes.md"' in start
        assert 'src="../images/picture.webp"' in start

    def test_the_chrome_names_the_version_and_the_online_copy(self, site: DocumentationSite) -> None:
        index = site.index.read_text(encoding="utf-8")

        assert f"SampleToNES {VERSION}" in index
        assert f'href="{ADDRESS}/index.md"' in index

    def test_the_same_documents_make_the_same_site(self, site: DocumentationSite, request_for: SiteRequest) -> None:
        stamp = site.read_stamp()

        assert build_site(request_for).read_stamp() == stamp

    def test_an_earlier_site_is_replaced(self, site: DocumentationSite, request_for: SiteRequest) -> None:
        stale = site.directory / "guide" / "removed.html"
        stale.write_text("stale", encoding="utf-8")

        build_site(request_for)

        assert not stale.exists()


class TestBuildSiteRefuses:
    def test_a_folder_holding_other_files(self, request_for: SiteRequest) -> None:
        request_for.output.mkdir()
        keep = request_for.output / "notes.txt"
        keep.write_text("mine", encoding="utf-8")

        with pytest.raises(OutputOccupiedError):
            build_site(request_for)

        assert keep.read_text(encoding="utf-8") == "mine"

    def test_a_broken_link(self, request_for: SiteRequest) -> None:
        (request_for.docs / "guide" / "next.md").write_text("# Next steps\n\n[Gone](gone.md)\n", encoding="utf-8")

        with pytest.raises(BrokenLinkError):
            build_site(request_for)

    def test_a_missing_picture(self, request_for: SiteRequest) -> None:
        (request_for.docs / "images" / "picture.webp").unlink()

        with pytest.raises(BrokenLinkError):
            build_site(request_for)
