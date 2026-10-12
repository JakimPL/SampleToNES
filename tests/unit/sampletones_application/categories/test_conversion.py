from pathlib import Path
from typing import Final, Tuple

import pytest

from sampletones_application.categories.conversion import MAX_REPORTED_RECORDINGS, SkippedRecordingMessages
from sampletones_application.categories.skipped import ROW_BULLET
from tests.suite.base import BaseTestSuite
from tests.suite.language import FakeLanguageManager

ONE: Final[str] = "one skipped:"
SEVERAL: Final[str] = "{count} skipped:"
MORE: Final[str] = "and {count} more"
FOLDER: Final[Path] = Path("/samples/drums")


def _recordings(count: int) -> Tuple[Path, ...]:
    return tuple(FOLDER / f"hit {index:03d}.wav" for index in range(count))


@pytest.fixture(name="messages")
def messages_fixture() -> SkippedRecordingMessages:
    return SkippedRecordingMessages.build(
        FakeLanguageManager(
            {
                "main.converter.message.skipped_recording_heading": ONE,
                "main.converter.template.skipped_recordings_heading": SEVERAL,
                "main.converter.template.skipped_recordings_more": MORE,
            }
        )
    )


class TestTheRecordingsABatchSkipped(BaseTestSuite):
    """The end of a batch counts the recordings it skipped, names each by file, and cuts a long list."""

    def test_a_batch_that_skipped_nothing_says_nothing(self, messages: SkippedRecordingMessages) -> None:
        assert messages.notice(()) is None

    def test_one_skipped_recording_stands_under_its_own_heading(self, messages: SkippedRecordingMessages) -> None:
        assert messages.notice(_recordings(1)) == f"{ONE}\n{ROW_BULLET}hit 000.wav"

    def test_several_are_counted_and_named_by_file(self, messages: SkippedRecordingMessages) -> None:
        assert messages.notice(_recordings(2)) == f"2 skipped:\n{ROW_BULLET}hit 000.wav\n{ROW_BULLET}hit 001.wav"

    def test_a_long_list_is_cut_and_counts_the_rest(self, messages: SkippedRecordingMessages) -> None:
        extra = 3
        notice = messages.notice(_recordings(MAX_REPORTED_RECORDINGS + extra))

        assert notice is not None
        lines = notice.split("\n")
        assert lines[0] == f"{MAX_REPORTED_RECORDINGS + extra} skipped:"
        assert len(lines) == MAX_REPORTED_RECORDINGS + 2
        assert lines[-1] == f"and {extra} more"

    def test_a_list_that_fits_names_every_recording(self, messages: SkippedRecordingMessages) -> None:
        notice = messages.notice(_recordings(MAX_REPORTED_RECORDINGS))

        assert notice is not None
        assert len(notice.split("\n")) == MAX_REPORTED_RECORDINGS + 1
