import pytest
from pydantic import ValidationError

from sampletones_player.compression.dictionary.phrase import Phrase
from sampletones_player.specification.compression import (
    MAX_PHRASE_LENGTH,
    PHRASE_LENGTH_SIZE,
    PHRASE_TABLE_ENTRY_SIZE,
)
from tests.unit.sampletones_player.compression.dictionary.phrases import phrase


class TestAPhraseIsAShapeRatherThanValues:
    """What identifies a phrase is the step from each value to the next, which a shift leaves alone."""

    def test_the_steps_read_the_body_pairwise(self) -> None:
        assert phrase(10, 12, 9).differences == bytes((2, 253))

    def test_a_shifted_phrase_keeps_the_steps_of_the_one_it_was_stored_from(self) -> None:
        assert phrase(70, 72, 69).differences == phrase(10, 12, 9).differences

    def test_a_phrase_covers_the_ticks_its_body_states(self) -> None:
        assert phrase(1, 2, 3).length == 3

    def test_a_phrase_costs_its_entry_its_length_and_its_body(self) -> None:
        assert phrase(1, 2, 3).size == PHRASE_TABLE_ENTRY_SIZE + PHRASE_LENGTH_SIZE + 3

    def test_a_body_reaching_past_a_length_byte_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            Phrase(body=bytes(MAX_PHRASE_LENGTH + 1))

    def test_a_phrase_covering_no_tick_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            Phrase(body=b"")
