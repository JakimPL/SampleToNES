from typing import Final
from unittest.mock import MagicMock

import pytest

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.coordinators.failures import UnhandledFailurePresenter
from sampletones_application.paths import LANG_EN

LANGUAGE_MANAGER: Final[LanguageManager] = LanguageManager(LANG_EN)
UNEXPECTED_FAILURE: Final[str] = "global.dialog.message.unexpected_failure"


@pytest.fixture(name="dialogs")
def dialogs_fixture() -> MagicMock:
    return MagicMock()


class TestAnUnhandledFailure:
    """A failure nothing recovered from reads as a report opening with the line that the action stopped."""

    def test_it_reads_as_a_failure_report(self, dialogs: MagicMock) -> None:
        failure = RuntimeError("it went wrong")

        UnhandledFailurePresenter(dialogs=dialogs, language_manager=LANGUAGE_MANAGER).present(failure)

        dialogs.show_failure_report.assert_called_once_with(failure, LANGUAGE_MANAGER[UNEXPECTED_FAILURE])
