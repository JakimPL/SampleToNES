from dataclasses import dataclass
from typing import Optional

import pytest

from sampletones_application.logic.project.title.document import (
    ReconstructionTitlePart,
    document_title,
)
from sampletones_shared.constants.symbols import TITLE_SEPARATOR
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
        reconstruction_name: Optional[str]
        reconstruction_unsaved: bool
        reconstruction_included: bool
        expected: str

    test_cases = (
        TestCase(
            label="project_is_primary",
            project_name="Song",
            project_unsaved=False,
            project_open=True,
            reconstruction_name=None,
            reconstruction_unsaved=False,
            reconstruction_included=False,
            expected="Song",
        ),
        TestCase(
            label="unsaved_project_is_marked",
            project_name="Song",
            project_unsaved=True,
            project_open=True,
            reconstruction_name=None,
            reconstruction_unsaved=False,
            reconstruction_included=False,
            expected="Song*",
        ),
        TestCase(
            label="untitled_fallback",
            project_name="",
            project_unsaved=False,
            project_open=True,
            reconstruction_name=None,
            reconstruction_unsaved=False,
            reconstruction_included=False,
            expected="Untitled",
        ),
        TestCase(
            label="file_reconstruction_appended_after_separator_with_extension",
            project_name="Song",
            project_unsaved=False,
            project_open=True,
            reconstruction_name="Recon.stn",
            reconstruction_unsaved=True,
            reconstruction_included=False,
            expected=f"Song{TITLE_SEPARATOR}Recon.stn*",
        ),
        TestCase(
            label="included_reconstruction_shown_in_brackets",
            project_name="Song",
            project_unsaved=False,
            project_open=True,
            reconstruction_name="1A: kick",
            reconstruction_unsaved=False,
            reconstruction_included=True,
            expected="Song [1A: kick]",
        ),
        TestCase(
            label="included_reconstruction_defers_dirty_marker_to_project",
            project_name="Song",
            project_unsaved=True,
            project_open=True,
            reconstruction_name="1A: kick",
            reconstruction_unsaved=True,
            reconstruction_included=True,
            expected="Song* [1A: kick]",
        ),
        TestCase(
            label="closed_project_file_reconstruction_is_primary",
            project_name="",
            project_unsaved=False,
            project_open=False,
            reconstruction_name="Recon.stn",
            reconstruction_unsaved=False,
            reconstruction_included=False,
            expected="Recon.stn",
        ),
        TestCase(
            label="closed_project_no_reconstruction_is_empty",
            project_name="",
            project_unsaved=False,
            project_open=False,
            reconstruction_name=None,
            reconstruction_unsaved=False,
            reconstruction_included=False,
            expected="",
        ),
        TestCase(
            label="closed_project_unsaved_file_reconstruction_is_marked",
            project_name="",
            project_unsaved=False,
            project_open=False,
            reconstruction_name="Recon.stn",
            reconstruction_unsaved=True,
            reconstruction_included=False,
            expected="Recon.stn*",
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_document_title(self, test_case: TestCase) -> None:
        project = State(test_case.project_name, test_case.project_unsaved)
        reconstruction = (
            None
            if test_case.reconstruction_name is None
            else ReconstructionTitlePart(
                name=test_case.reconstruction_name,
                unsaved_changes=test_case.reconstruction_unsaved,
                included=test_case.reconstruction_included,
            )
        )
        result = document_title(
            project,
            reconstruction,
            untitled=UNTITLED,
            project_open=test_case.project_open,
        )
        assert result == test_case.expected
