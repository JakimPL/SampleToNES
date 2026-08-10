from dataclasses import dataclass

import pytest

from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.scripts import load_script

check_version_tag = load_script("ci/checks/version_tag.py")


class TestVersionFromTag(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        tag: str
        expected: str

    test_cases = (
        TestCase(
            label="release_tag",
            tag="v0.3.0",
            expected="0.3.0",
        ),
        TestCase(
            label="prerelease_tag",
            tag="v0.3.0.dev1",
            expected="0.3.0.dev1",
        ),
        TestCase(
            label="release_candidate",
            tag="v1.0.0rc2",
            expected="1.0.0rc2",
        ),
        TestCase(
            label="bare_version",
            tag="0.3.0",
            expected="0.3.0",
        ),
        TestCase(
            label="single_prefix_is_dropped",
            tag="vv0.3.0",
            expected="v0.3.0",
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_version_from_tag(self, test_case: TestCase) -> None:
        assert check_version_tag.version_from_tag(test_case.tag) == test_case.expected


class TestTagNamesVersion(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        tag: str
        project_version: str
        expected: bool

    test_cases = (
        TestCase(
            label="tag_matches",
            tag="v0.3.0",
            project_version="0.3.0",
            expected=True,
        ),
        TestCase(
            label="prerelease_matches",
            tag="v0.3.0.dev1",
            project_version="0.3.0.dev1",
            expected=True,
        ),
        TestCase(
            label="patch_differs",
            tag="v0.3.1",
            project_version="0.3.0",
            expected=False,
        ),
        TestCase(
            label="project_ahead_of_tag",
            tag="v0.3.0",
            project_version="0.4.0",
            expected=False,
        ),
        TestCase(
            label="prerelease_against_release",
            tag="v0.3.0",
            project_version="0.3.0.dev1",
            expected=False,
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_tag_names_version(
        self,
        test_case: TestCase,
    ) -> None:
        result = check_version_tag.tag_names_version(
            tag=test_case.tag,
            project_version=test_case.project_version,
        )

        assert result is test_case.expected


class TestMain:
    def test_matching_version_succeeds(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        assert (
            check_version_tag.main(
                ["--tag", "v0.3.0", "--project-version", "0.3.0"],
            )
            == 0
        )
        assert "matches" in capsys.readouterr().out

    def test_mismatched_version_is_annotated_as_an_error(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        assert (
            check_version_tag.main(
                ["--tag", "v0.3.1", "--project-version", "0.3.0"],
            )
            == 1
        )

        output = capsys.readouterr().out
        assert output.startswith("::error::")
        assert "v0.3.1" in output
        assert "0.3.0" in output
