from pathlib import Path

import pytest

from bootstrap.layout import (
    BUILD_TOOLS,
    DISTRIBUTION,
    DOCUMENTATION_FILES,
    DOCUMENTATION_PACKAGE_PATH,
    DOCUMENTATION_SITE,
    GPU_PACKAGES,
    NOTICES,
    SOURCE_DIRECTORY,
)
from bootstrap.platforms.linux import Linux
from bootstrap.platforms.macos import MacOS
from hatch_build import SITE_DESTINATION
from sampletones_shared.documentation.site import DOCUMENTATION_DIRECTORY, INDEX_FILE, STAMP_FILE
from sampletones_shared.paths.resources import ASSETS_PACKAGE
from tests.suite.bootstrap import PROJECT_NAME, RecordingRunner, write_project
from tests.suite.scripts import load_script

verify_bundle = load_script("verify_bundle.py")


@pytest.fixture(name="root")
def root_fixture(tmp_path: Path) -> Path:
    """A repository holding a release bundle with its notices, its documentation and its launcher."""
    launcher = Linux().bundling().launcher(tmp_path / DISTRIBUTION, name=PROJECT_NAME, directory=True)
    launcher.parent.mkdir(parents=True)
    launcher.write_bytes(b"launcher")
    for name in NOTICES:
        (launcher.parent / name).write_text(name)

    site = _site(launcher.parent)
    site.mkdir(parents=True)
    for name in DOCUMENTATION_FILES:
        (site / name).write_text(name)

    return write_project(tmp_path)


def _bundle(root: Path) -> Path:
    return root / DISTRIBUTION / PROJECT_NAME


def _site(bundle: Path) -> Path:
    return bundle / verify_bundle.INTERNAL_DIRECTORY / DOCUMENTATION_PACKAGE_PATH


class TestMissingNotices:
    def test_a_complete_bundle_lacks_nothing(self, root: Path) -> None:
        assert verify_bundle.missing_notices(_bundle(root)) == []

    def test_every_absent_notice_is_reported(self, root: Path) -> None:
        for name in NOTICES[1:]:
            (_bundle(root) / name).unlink()

        assert verify_bundle.missing_notices(_bundle(root)) == list(NOTICES[1:])

    def test_a_notice_directory_counts_as_absent(self, root: Path) -> None:
        (_bundle(root) / NOTICES[0]).unlink()
        (_bundle(root) / NOTICES[0]).mkdir()

        assert verify_bundle.missing_notices(_bundle(root)) == [NOTICES[0]]


class TestMissingDocumentation:
    def test_a_complete_bundle_lacks_nothing(self, root: Path) -> None:
        assert verify_bundle.missing_documentation(_bundle(root)) == []

    def test_an_unsealed_site_is_reported(self, root: Path) -> None:
        (_site(_bundle(root)) / DOCUMENTATION_FILES[1]).unlink()

        assert verify_bundle.missing_documentation(_bundle(root)) == [DOCUMENTATION_FILES[1]]

    def test_a_bundle_without_pages_is_reported(self, root: Path) -> None:
        for name in DOCUMENTATION_FILES:
            (_site(_bundle(root)) / name).unlink()

        assert verify_bundle.missing_documentation(_bundle(root)) == list(DOCUMENTATION_FILES)


class TestTheDocumentationContract:
    """The scripts run on the standard library alone, so they spell the site's place themselves; it has
    to be the place the application reads and the build hook writes."""

    def test_the_package_path_is_the_one_the_application_reads(self) -> None:
        assert DOCUMENTATION_PACKAGE_PATH == f"{ASSETS_PACKAGE}/{DOCUMENTATION_DIRECTORY}" == SITE_DESTINATION

    def test_the_checkout_site_lies_in_the_source_package(self) -> None:
        assert DOCUMENTATION_SITE == f"{SOURCE_DIRECTORY}/{DOCUMENTATION_PACKAGE_PATH}"

    def test_the_files_are_the_index_and_the_stamp(self) -> None:
        assert DOCUMENTATION_FILES == (INDEX_FILE, STAMP_FILE)


class TestCarriedBuildTools:
    def test_an_application_bundle_holds_to_its_notices(self, root: Path) -> None:
        assert verify_bundle.carried_build_tools(_bundle(root)) == []

    def test_a_build_tool_beside_the_application_is_reported(self, root: Path) -> None:
        (_bundle(root) / verify_bundle.INTERNAL_DIRECTORY / BUILD_TOOLS[0]).mkdir(parents=True)

        assert verify_bundle.carried_build_tools(_bundle(root)) == [BUILD_TOOLS[0]]

    def test_a_build_tool_beside_the_launcher_is_reported(self, root: Path) -> None:
        (_bundle(root) / BUILD_TOOLS[0]).mkdir()

        assert verify_bundle.carried_build_tools(_bundle(root)) == [BUILD_TOOLS[0]]


class TestCarriedGpuPackages:
    def test_a_cpu_bundle_carries_none(self, root: Path) -> None:
        assert verify_bundle.carried_gpu_packages(_bundle(root)) == []

    def test_every_gpu_package_among_the_internals_is_reported(self, root: Path) -> None:
        for name in GPU_PACKAGES:
            (_bundle(root) / verify_bundle.INTERNAL_DIRECTORY / name).mkdir(parents=True)

        assert verify_bundle.carried_gpu_packages(_bundle(root)) == list(GPU_PACKAGES)


class TestBundleFailures:
    def test_a_complete_bundle_passes_once_its_launcher_starts(self, root: Path) -> None:
        runner = RecordingRunner({}, None)

        assert verify_bundle.bundle_failures(root, Linux(), runner=runner, environment={}) == []
        assert runner.lines == [f"{_bundle(root) / PROJECT_NAME} {verify_bundle.VERSION_FLAG}"]

    def test_a_missing_notice_is_named(self, root: Path) -> None:
        (_bundle(root) / NOTICES[1]).unlink()

        failures = verify_bundle.bundle_failures(root, Linux(), runner=RecordingRunner({}, None), environment={})

        assert len(failures) == 1
        assert NOTICES[1] in failures[0]

    def test_a_missing_documentation_is_named(self, root: Path) -> None:
        (_site(_bundle(root)) / DOCUMENTATION_FILES[0]).unlink()

        failures = verify_bundle.bundle_failures(root, Linux(), runner=RecordingRunner({}, None), environment={})

        assert [DOCUMENTATION_FILES[0] in failure for failure in failures] == [True]

    def test_bundled_build_tooling_is_named(self, root: Path) -> None:
        (_bundle(root) / verify_bundle.INTERNAL_DIRECTORY / BUILD_TOOLS[0]).mkdir(parents=True)

        failures = verify_bundle.bundle_failures(root, Linux(), runner=RecordingRunner({}, None), environment={})

        assert [BUILD_TOOLS[0] in failure for failure in failures] == [True]

    def test_a_release_built_with_gpu_support_is_named(self, root: Path) -> None:
        (_bundle(root) / verify_bundle.INTERNAL_DIRECTORY / GPU_PACKAGES[0]).mkdir(parents=True)

        failures = verify_bundle.bundle_failures(root, Linux(), runner=RecordingRunner({}, None), environment={})

        assert [GPU_PACKAGES[0] in failure for failure in failures] == [True]

    def test_a_missing_launcher_is_named_and_nothing_runs(self, root: Path) -> None:
        (_bundle(root) / PROJECT_NAME).unlink()
        runner = RecordingRunner({}, None)

        failures = verify_bundle.bundle_failures(root, Linux(), runner=runner, environment={})

        assert [("offers no launcher" in failure) for failure in failures] == [True]
        assert runner.lines == []

    def test_a_launcher_that_fails_is_named_with_its_status(self, root: Path) -> None:
        failures = verify_bundle.bundle_failures(
            root,
            Linux(),
            runner=RecordingRunner({verify_bundle.VERSION_FLAG: 3}, None),
            environment={},
        )

        assert [("status 3" in failure) for failure in failures] == [True]

    def test_a_system_without_bundles_is_refused(self, root: Path) -> None:
        with pytest.raises(SystemExit, match="make setup"):
            verify_bundle.bundle_failures(root, MacOS(), runner=RecordingRunner({}, None), environment={})
