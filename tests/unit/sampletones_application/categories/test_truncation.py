from typing import Final

import pytest

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.categories.truncation import TruncationMessages
from sampletones_application.paths import LANG_EN
from sampletones_core.exporters.truncation import EnvelopeTruncation

SHORTENED: Final[EnvelopeTruncation] = EnvelopeTruncation(frames=512, source_frames=600, instruments=3)


@pytest.fixture(name="messages")
def messages_fixture() -> TruncationMessages:
    return TruncationMessages.for_project(LanguageManager(LANG_EN))


class TestTheReportOfShortenedInstruments:
    def test_an_export_written_whole_has_nothing_to_report(self, messages: TruncationMessages) -> None:
        assert messages.notice(None) is None

    def test_a_shortened_export_names_the_instruments_and_the_frames_they_keep(
        self,
        messages: TruncationMessages,
    ) -> None:
        notice = messages.notice(SHORTENED)
        assert notice is not None
        assert str(SHORTENED.instruments) in notice
        assert str(SHORTENED.frames) in notice
