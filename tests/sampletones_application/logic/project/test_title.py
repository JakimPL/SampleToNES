from dataclasses import dataclass

import pytest

from sampletones_application.logic.project.title import document_title, is_any_unsaved
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase


@dataclass
class State:
    name: str
    unsaved_changes: bool


UNTITLED = "Untitled"


class TestDocumentTitle(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        project_name: str
        project_unsaved: bool
        project_open: bool
        reconstruction_name: str
        reconstruction_unsaved: bool
        reconstruction_loaded: bool
        expected: str

    test_cases = [
        TestCase(
            label="project_is_primary",
            project_name="Song",
            project_unsaved=False,
            project_open=True,
            reconstruction_name="Recon",
            reconstruction_unsaved=False,
            reconstruction_loaded=False,
            expected="Song",
        ),
        TestCase(
            label="unsaved_project_is_marked",
            project_name="Song",
            project_unsaved=True,
            project_open=True,
            reconstruction_name="",
            reconstruction_unsaved=False,
            reconstruction_loaded=False,
            expected="Song*",
        ),
        TestCase(
            label="untitled_fallback",
            project_name="",
            project_unsaved=False,
            project_open=True,
            reconstruction_name="",
            reconstruction_unsaved=False,
            reconstruction_loaded=False,
            expected="Untitled",
        ),
        TestCase(
            label="reconstruction_appended_as_secondary",
            project_name="Song",
            project_unsaved=False,
            project_open=True,
            reconstruction_name="Recon",
            reconstruction_unsaved=True,
            reconstruction_loaded=True,
            expected="Song — Recon*",
        ),
        TestCase(
            label="closed_project_reconstruction_is_primary",
            project_name="",
            project_unsaved=False,
            project_open=False,
            reconstruction_name="Recon",
            reconstruction_unsaved=False,
            reconstruction_loaded=True,
            expected="Recon",
        ),
        TestCase(
            label="closed_project_no_reconstruction_is_empty",
            project_name="",
            project_unsaved=False,
            project_open=False,
            reconstruction_name="",
            reconstruction_unsaved=False,
            reconstruction_loaded=False,
            expected="",
        ),
        TestCase(
            label="closed_project_unsaved_reconstruction_is_marked",
            project_name="",
            project_unsaved=False,
            project_open=False,
            reconstruction_name="Recon",
            reconstruction_unsaved=True,
            reconstruction_loaded=True,
            expected="Recon*",
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_document_title(self, test_case: TestCase) -> None:
        project = State(test_case.project_name, test_case.project_unsaved)
        reconstruction = State(test_case.reconstruction_name, test_case.reconstruction_unsaved)
        result = document_title(
            project,
            reconstruction,
            untitled=UNTITLED,
            project_open=test_case.project_open,
            reconstruction_loaded=test_case.reconstruction_loaded,
        )
        assert result == test_case.expected


class TestIsAnyUnsaved:
    def test_either_unsaved(self) -> None:
        assert is_any_unsaved(State("a", False), State("b", True)) is True
        assert is_any_unsaved(State("a", True), State("b", False)) is True

    def test_both_clean(self) -> None:
        assert is_any_unsaved(State("a", False), State("b", False)) is False
