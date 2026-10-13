from pathlib import Path
from typing import Final, List

import pytest

from assets.documentation.__main__ import DocumentationArguments, main
from assets.documentation.build import SiteRequest
from assets.documentation.paths import DOCS_DIRECTORY, PROJECT_FILE, SITE_DIRECTORY
from sampletones_shared.documentation.site import DocumentationSite

BUILDER: Final[str] = "assets.documentation.__main__.build_site"


class RecordedBuilds:
    def __init__(self) -> None:
        self.requests: List[SiteRequest] = []

    def __call__(self, request: SiteRequest) -> DocumentationSite:
        self.requests.append(request)
        return DocumentationSite(request.output)


class TestDocumentationArguments:
    def test_without_an_output_the_package_folder_is_named(self) -> None:
        assert DocumentationArguments.parse([]).directory == SITE_DIRECTORY

    def test_an_output_of_its_own_is_named(self, tmp_path: Path) -> None:
        assert DocumentationArguments.parse(["-o", str(tmp_path)]).directory == tmp_path


class TestMain:
    def test_the_checkout_docs_are_written_where_asked(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        tmp_path: Path,
    ) -> None:
        builds = RecordedBuilds()
        monkeypatch.setattr(BUILDER, builds)

        assert main(["--output", str(tmp_path)]) == 0
        assert builds.requests == [SiteRequest(docs=DOCS_DIRECTORY, project=PROJECT_FILE, output=tmp_path)]
        assert f"Wrote {tmp_path / 'index.html'}" in capsys.readouterr().out
