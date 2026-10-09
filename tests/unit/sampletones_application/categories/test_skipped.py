from typing import Final, List

import pytest

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.categories.skipped import MAX_REPORTED_ROWS, SkippedRowMessages
from sampletones_application.paths import LANG_EN
from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters.skipped import SkippedRow, SkipReason
from sampletones_core.project.voices.sample import Sample
from sampletones_core.structures import IdentifiedCollection
from tests.suite.sequencer import sample_reconstruction

ROWS_LISTED: Final[int] = MAX_REPORTED_ROWS


def _skipped(
    voice_id: str,
    *,
    order_position: int = 3,
    row_index: int = 26,
    reason: SkipReason = SkipReason.NO_INSTRUMENT,
) -> SkippedRow:
    return SkippedRow(
        voice_id=voice_id,
        channel=ChannelName.PULSE1,
        order_position=order_position,
        row_index=row_index,
        reason=reason,
    )


@pytest.fixture(name="messages")
def messages_fixture() -> SkippedRowMessages:
    return SkippedRowMessages.build(LanguageManager(LANG_EN))


@pytest.fixture(name="voices")
def voices_fixture() -> IdentifiedCollection[Sample]:
    voices: IdentifiedCollection[Sample] = IdentifiedCollection()
    for name in ("Lead", "Bass"):
        voices.append(Sample(name=name, reconstruction=sample_reconstruction([ChannelName.TRIANGLE])))

    return voices


class TestTheReportOfRowsLeftSilent:
    def test_an_export_that_left_no_row_silent_has_nothing_to_report(
        self,
        messages: SkippedRowMessages,
        voices: IdentifiedCollection[Sample],
    ) -> None:
        assert messages.notice((), voices) is None

    def test_a_row_is_named_by_its_frame_channel_and_row_in_hexadecimal(
        self,
        messages: SkippedRowMessages,
        voices: IdentifiedCollection[Sample],
    ) -> None:
        bass = voices[1]

        notice = messages.notice((_skipped(bass.id),), voices)

        assert notice is not None
        assert "Frame 03, Pulse 1, row 1A: " in notice

    def test_the_voice_reads_as_the_voices_list_prints_it(
        self,
        messages: SkippedRowMessages,
        voices: IdentifiedCollection[Sample],
    ) -> None:
        bass = voices[1]

        notice = messages.notice((_skipped(bass.id),), voices)

        assert notice is not None
        assert notice.endswith("01: Bass")

    def test_a_voice_the_project_no_longer_holds_reads_blank(
        self,
        messages: SkippedRowMessages,
        voices: IdentifiedCollection[Sample],
    ) -> None:
        notice = messages.notice((_skipped("a-voice-no-project-holds"),), voices)

        assert notice is not None
        assert notice.endswith(": ..")

    def test_the_report_opens_on_its_heading(
        self,
        messages: SkippedRowMessages,
        voices: IdentifiedCollection[Sample],
    ) -> None:
        notice = messages.notice((_skipped(voices[0].id),), voices)

        assert notice is not None
        assert notice.splitlines()[0] == messages.headings[SkipReason.NO_INSTRUMENT]

    def test_a_short_list_is_printed_whole(
        self,
        messages: SkippedRowMessages,
        voices: IdentifiedCollection[Sample],
    ) -> None:
        rows = tuple(_skipped(voices[0].id, row_index=index) for index in range(ROWS_LISTED))

        notice = messages.notice(rows, voices)

        assert notice is not None
        assert len(notice.splitlines()) == 1 + ROWS_LISTED
        assert "more" not in notice

    def test_a_long_list_is_cut_and_says_how_many_it_leaves_out(
        self,
        messages: SkippedRowMessages,
        voices: IdentifiedCollection[Sample],
    ) -> None:
        left_out = 5
        rows = tuple(_skipped(voices[0].id, row_index=index) for index in range(ROWS_LISTED + left_out))

        notice = messages.notice(rows, voices)

        assert notice is not None
        lines: List[str] = notice.splitlines()
        assert len(lines) == 1 + ROWS_LISTED + 1
        assert lines[-1] == f"and {left_out} more"


class TestTheReportGivesEachReasonAParagraph:
    """A note cut, a transpose left out and an instrument written at another frame's pitch are different
    things for the reader to fix, so each reason is reported under a heading of its own, the note cuts
    first.
    """

    def test_each_reason_opens_a_paragraph_of_its_own(
        self,
        messages: SkippedRowMessages,
        voices: IdentifiedCollection[Sample],
    ) -> None:
        rows = (
            _skipped(voices[0].id, reason=SkipReason.CARRIED_PITCH),
            _skipped(voices[0].id, reason=SkipReason.UNREACHED_TRANSPOSE),
            _skipped(voices[1].id),
        )

        notice = messages.notice(rows, voices)

        assert notice is not None
        paragraphs = notice.split("\n\n")
        assert [paragraph.splitlines()[0] for paragraph in paragraphs] == [
            messages.headings[SkipReason.NO_INSTRUMENT],
            messages.headings[SkipReason.UNREACHED_TRANSPOSE],
            messages.headings[SkipReason.CARRIED_PITCH],
        ]

    def test_every_reason_has_a_heading(self, messages: SkippedRowMessages) -> None:
        assert set(messages.headings) == set(SkipReason)
