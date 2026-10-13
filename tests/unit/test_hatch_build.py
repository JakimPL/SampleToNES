from pathlib import Path
from typing import Any, Dict, Final, List

import pytest

from assets.documentation.build import SiteRequest
from assets.documentation.paths import DOCS_DIRECTORY, PROJECT_FILE
from hatch_build import EDITABLE, FORCE_INCLUDE, SITE_DESTINATION, DocumentationBuildHook
from sampletones_shared.documentation.site import INDEX_FILE, DocumentationSite
from sampletones_shared.paths.source import REPOSITORY_ROOT

BUILDER: Final[str] = "assets.documentation.build.build_site"
STANDARD: Final[str] = "standard"


class RecordedBuilds:
    def __init__(self) -> None:
        self.requests: List[SiteRequest] = []

    def __call__(self, request: SiteRequest) -> DocumentationSite:
        self.requests.append(request)
        (request.output / INDEX_FILE).write_text("<p>index</p>", encoding="utf-8")
        site = DocumentationSite(request.output)
        site.write_stamp()
        return site


@pytest.fixture
def builds(monkeypatch: pytest.MonkeyPatch) -> RecordedBuilds:
    recorded = RecordedBuilds()
    monkeypatch.setattr(BUILDER, recorded)
    return recorded


@pytest.fixture
def hook(tmp_path: Path) -> DocumentationBuildHook:
    return DocumentationBuildHook(
        root=str(REPOSITORY_ROOT),
        config={},
        build_config=None,
        metadata=None,
        directory=str(tmp_path),
        target_name="wheel",
    )


@pytest.fixture
def build_data() -> Dict[str, Any]:
    return {FORCE_INCLUDE: {}}


class TestDocumentationBuildHook:
    def test_an_editable_build_carries_no_site(
        self,
        hook: DocumentationBuildHook,
        builds: RecordedBuilds,
        build_data: Dict[str, Any],
    ) -> None:
        hook.initialize(EDITABLE, build_data)

        assert builds.requests == []
        assert build_data == {FORCE_INCLUDE: {}}

    def test_a_wheel_carries_the_checkout_docs_at_the_package_path(
        self,
        hook: DocumentationBuildHook,
        builds: RecordedBuilds,
        build_data: Dict[str, Any],
    ) -> None:
        hook.initialize(STANDARD, build_data)

        [(source, destination)] = build_data[FORCE_INCLUDE].items()
        assert destination == SITE_DESTINATION
        assert builds.requests == [SiteRequest(docs=DOCS_DIRECTORY, project=PROJECT_FILE, output=Path(source))]
        assert DocumentationSite(Path(source)).read_stamp() is not None

        hook.finalize(STANDARD, build_data, "sampletones.whl")

    def test_the_site_is_removed_once_the_wheel_is_written(
        self,
        hook: DocumentationBuildHook,
        builds: RecordedBuilds,
        build_data: Dict[str, Any],
    ) -> None:
        hook.initialize(STANDARD, build_data)
        [source] = build_data[FORCE_INCLUDE]

        hook.finalize(STANDARD, build_data, "sampletones.whl")

        assert len(builds.requests) == 1
        assert not Path(source).exists()
