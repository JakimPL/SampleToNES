from dataclasses import dataclass

import pytest

from bootstrap.layout import repository_root
from bootstrap.project import read_project
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.scripts import load_script

verify_version_tag = load_script("verify_version_tag.py")


class TestVersionFromTag(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        tag: str
        expected: str

    test_cases = (
        TestCase(label="release_tag", tag="v0.3.0", expected="0.3.0"),
        TestCase(label="prerelease_tag", tag="v0.3.0.dev1", expected="0.3.0.dev1"),
        TestCase(label="release_candidate", tag="v1.0.0rc2", expected="1.0.0rc2"),
        TestCase(label="bare_version", tag="0.3.0", expected="0.3.0"),
        TestCase(label="single_prefix_is_dropped", tag="vv0.3.0", expected="v0.3.0"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_version_from_tag(self, test_case: TestCase) -> None:
        assert verify_version_tag.version_from_tag(test_case.tag) == test_case.expected


class TestMain:
    def test_the_tag_naming_the_project_version_passes(self) -> None:
        version = read_project(repository_root()).version

        assert verify_version_tag.main(["--tag", f"{verify_version_tag.TAG_PREFIX}{version}"]) == 0

    def test_a_tag_naming_another_version_is_annotated_as_an_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        version = read_project(repository_root()).version

        assert verify_version_tag.main(["--tag", f"{verify_version_tag.TAG_PREFIX}{version}.post9"]) == 1
        assert capsys.readouterr().out.startswith("::error::")
