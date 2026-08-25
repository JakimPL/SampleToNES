import pytest
from pydantic import ValidationError

from sampletones_player.compression.dictionary.table import PhraseTable, phrase_table
from sampletones_player.specification.compression import (
    MAX_PHRASE_IDS,
    PHRASE_TABLE_COUNT_SIZE,
)
from tests.unit.sampletones_player.compression.dictionary.phrases import distinct, phrase


class TestTheTableHoldsWhatATokenCanName:
    """A phrase's position is its id, and the cheap ids ride inside an opcode."""

    def test_a_shape_offered_twice_is_held_once(self) -> None:
        table = phrase_table((phrase(1, 2), phrase(1, 2), phrase(3, 4)))
        assert table.phrases == (phrase(1, 2), phrase(3, 4))

    def test_a_phrase_is_reached_by_the_id_its_position_gives_it(self) -> None:
        table = phrase_table((phrase(1, 2), phrase(3, 4)))
        assert table[1] == phrase(3, 4)

    def test_the_table_stops_where_a_token_stops_naming(self) -> None:
        assert len(phrase_table(distinct(MAX_PHRASE_IDS + 10))) == MAX_PHRASE_IDS

    def test_a_table_beyond_the_ids_a_token_reaches_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            PhraseTable(phrases=tuple(distinct(MAX_PHRASE_IDS + 1)))

    def test_the_dictionary_costs_its_count_and_its_phrases(self) -> None:
        table = phrase_table((phrase(1, 2), phrase(3, 4, 5)))
        assert table.size == PHRASE_TABLE_COUNT_SIZE + phrase(1, 2).size + phrase(3, 4, 5).size
