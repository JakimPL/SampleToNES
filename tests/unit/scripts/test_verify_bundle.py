from pathlib import Path

import pytest

from bootstrap.layout import BUILD_TOOLS, DISTRIBUTION, NOTICES
from bootstrap.platforms.linux import Linux
from bootstrap.platforms.macos import MacOS
from tests.suite.bootstrap import PROJECT_NAME, RecordingRunner, write_project
from tests.suite.scripts import load_script

verify_bundle = load_script("verify_bundle.py")


@pytest.fixture(name="root")
def root_fixture(tmp_path: Path) -> Path:
    """A repository holding a release bundle with its notices and its launcher."""
    launcher = Linux().bundling().launcher(tmp_path / DISTRIBUTION, name=PROJECT_NAME, release=True)
    launcher.parent.mkdir(parents=True)
    launcher.write_bytes(b"launcher")
    for name in NOTICES:
        (launcher.parent / name).write_text(name)

    return write_project(tmp_path)


def _bundle(root: Path) -> Path:
    return root / DISTRIBUTION / PROJECT_NAME


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


class TestCarriedBuildTools:
    def test_an_application_bundle_holds_to_its_notices(self, root: Path) -> None:
        assert verify_bundle.carried_build_tools(_bundle(root)) == []

    def test_a_build_tool_beside_the_application_is_reported(self, root: Path) -> None:
        (_bundle(root) / verify_bundle.INTERNAL_DIRECTORY / BUILD_TOOLS[0]).mkdir(parents=True)

        assert verify_bundle.carried_build_tools(_bundle(root)) == [BUILD_TOOLS[0]]

    def test_a_build_tool_beside_the_launcher_is_reported(self, root: Path) -> None:
        (_bundle(root) / BUILD_TOOLS[0]).mkdir()

        assert verify_bundle.carried_build_tools(_bundle(root)) == [BUILD_TOOLS[0]]


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

    def test_bundled_build_tooling_is_named(self, root: Path) -> None:
        (_bundle(root) / verify_bundle.INTERNAL_DIRECTORY / BUILD_TOOLS[0]).mkdir(parents=True)

        failures = verify_bundle.bundle_failures(root, Linux(), runner=RecordingRunner({}, None), environment={})

        assert [BUILD_TOOLS[0] in failure for failure in failures] == [True]

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
