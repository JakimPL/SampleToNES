from pathlib import Path
from typing import Any, Dict, Final, List

import pytest

from assets.documentation.build import SiteRequest
from assets.documentation.paths import DOCS_DIRECTORY, PROJECT_FILE
from hatch_build import (
    DEPLOYMENT_DESTINATION,
    DEVELOPMENT_WHEEL,
    DEVELOPMENT_WHEEL_ENABLED,
    EDITABLE,
    FORCE_INCLUDE,
    RELEASE_DEPLOYMENT,
    SITE_DESTINATION,
    DistributionBuildHook,
)
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


@pytest.fixture(autouse=True)
def _distribution_wheel(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(DEVELOPMENT_WHEEL, raising=False)


@pytest.fixture
def hook(tmp_path: Path) -> DistributionBuildHook:
    return DistributionBuildHook(
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


def _source_of(build_data: Dict[str, Any], destination: str) -> Path:
    [source] = [source for source, target in build_data[FORCE_INCLUDE].items() if target == destination]
    return Path(source)


class TestDistributionBuildHook:
    def test_an_editable_build_carries_no_site(
        self,
        hook: DistributionBuildHook,
        builds: RecordedBuilds,
        build_data: Dict[str, Any],
    ) -> None:
        hook.initialize(EDITABLE, build_data)

        assert builds.requests == []
        assert build_data == {FORCE_INCLUDE: {}}

    def test_a_wheel_carries_the_checkout_docs_at_the_package_path(
        self,
        hook: DistributionBuildHook,
        builds: RecordedBuilds,
        build_data: Dict[str, Any],
    ) -> None:
        hook.initialize(STANDARD, build_data)

        site = _source_of(build_data, SITE_DESTINATION)
        assert builds.requests == [SiteRequest(docs=DOCS_DIRECTORY, project=PROJECT_FILE, output=site)]
        assert DocumentationSite(site).read_stamp() is not None

        hook.finalize(STANDARD, build_data, "sampletones.whl")

    def test_a_wheel_carries_the_release_deployment_from_outside_the_checkout(
        self,
        hook: DistributionBuildHook,
        builds: RecordedBuilds,
        build_data: Dict[str, Any],
    ) -> None:
        hook.initialize(STANDARD, build_data)

        deployment = _source_of(build_data, DEPLOYMENT_DESTINATION)
        assert deployment.read_bytes() == (REPOSITORY_ROOT / RELEASE_DEPLOYMENT).read_bytes()
        assert REPOSITORY_ROOT not in deployment.parents
        assert len(builds.requests) == 1

        hook.finalize(STANDARD, build_data, "sampletones.whl")

    def test_a_development_wheel_keeps_the_checkout_deployment(
        self,
        hook: DistributionBuildHook,
        builds: RecordedBuilds,
        build_data: Dict[str, Any],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv(DEVELOPMENT_WHEEL, DEVELOPMENT_WHEEL_ENABLED)

        hook.initialize(STANDARD, build_data)

        assert list(build_data[FORCE_INCLUDE].values()) == [SITE_DESTINATION]
        assert len(builds.requests) == 1

        hook.finalize(STANDARD, build_data, "sampletones.whl")

    def test_the_site_and_the_deployment_copy_are_removed_once_the_wheel_is_written(
        self,
        hook: DistributionBuildHook,
        builds: RecordedBuilds,
        build_data: Dict[str, Any],
    ) -> None:
        hook.initialize(STANDARD, build_data)
        site = _source_of(build_data, SITE_DESTINATION)
        deployment = _source_of(build_data, DEPLOYMENT_DESTINATION)

        hook.finalize(STANDARD, build_data, "sampletones.whl")

        assert len(builds.requests) == 1
        assert not site.exists()
        assert not deployment.parent.exists()
