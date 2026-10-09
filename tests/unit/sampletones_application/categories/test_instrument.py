import pytest

from sampletones_application.categories.instrument import (
    OMISSION_BULLET,
    OMISSION_ELEMENTS,
    InstrumentImportMessages,
)
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.paths import LANG_EN
from sampletones_core.formats.famitracker.voice import InstrumentOmission


@pytest.fixture
def messages() -> InstrumentImportMessages:
    return InstrumentImportMessages.build(LanguageManager(LANG_EN))


class TestEveryDimensionIsNamed:
    """A dimension a file states past the voice reaches the reader in words, never as an enum."""

    def test_each_one_a_reader_can_meet_carries_words(self, messages: InstrumentImportMessages) -> None:
        assert set(messages.omissions) == set(InstrumentOmission)
        assert all(messages.omissions[omission] for omission in InstrumentOmission)

    def test_each_one_reads_differently_from_the_rest(self, messages: InstrumentImportMessages) -> None:
        assert len(set(messages.omissions.values())) == len(InstrumentOmission)

    def test_the_map_answers_for_every_dimension(self) -> None:
        assert set(OMISSION_ELEMENTS) == set(InstrumentOmission)


class TestTheNotice:
    def test_a_file_stating_the_voice_alone_is_reported_nowhere(
        self,
        messages: InstrumentImportMessages,
    ) -> None:
        """An import that lost nothing has nothing to say, so no dialog interrupts it."""
        assert messages.notice("Lead", ()) is None

    def test_the_voice_is_named_in_the_opening(self, messages: InstrumentImportMessages) -> None:
        notice = messages.notice("Lead", (InstrumentOmission.CUMULATIVE_BEND,))

        assert notice is not None
        assert "Lead" in notice.splitlines()[0]

    def test_each_dimension_is_listed_on_its_own_line(self, messages: InstrumentImportMessages) -> None:
        stated = (InstrumentOmission.CUMULATIVE_BEND, InstrumentOmission.RELEASE_POINT)
        notice = messages.notice("Lead", stated)

        assert notice is not None
        assert [line for line in notice.splitlines() if line.startswith(OMISSION_BULLET)] == [
            f"{OMISSION_BULLET}{messages.omissions[omission]}" for omission in stated
        ]

    def test_a_dimension_the_file_left_out_is_named_nowhere(
        self,
        messages: InstrumentImportMessages,
    ) -> None:
        notice = messages.notice("Lead", (InstrumentOmission.CUMULATIVE_BEND,))

        assert notice is not None
        assert messages.omissions[InstrumentOmission.RELEASE_POINT] not in notice

    def test_a_file_stating_everything_names_everything(self, messages: InstrumentImportMessages) -> None:
        notice = messages.notice("Lead", tuple(InstrumentOmission))

        assert notice is not None
        assert all(words in notice for words in messages.omissions.values())

    def test_the_wording_holds_no_placeholder_open(self, messages: InstrumentImportMessages) -> None:
        notice = messages.notice("Lead", (InstrumentOmission.CUMULATIVE_BEND,))

        assert notice is not None
        assert "{" not in notice
