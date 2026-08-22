from typing import Final

from sampletones_player.compression.decode import decode_plane
from sampletones_player.compression.dictionary.phrase import Phrase
from sampletones_player.compression.dictionary.table import phrase_table
from sampletones_player.specification.compression import PHRASE_ID_ESCAPE, TokenTag

MOTIF: Final[bytes] = bytes((40, 44, 47))
DICTIONARY = phrase_table((Phrase(body=MOTIF),))


class TestWhatTheDriverReadsFromAStream:
    """The decoder is the reading the 6502 performs, stated where it is testable."""

    def test_a_literal_writes_the_values_that_follow_it(self) -> None:
        stream = bytes((TokenTag.LITERAL | 2, 5, 6, 7))
        assert decode_plane(stream, DICTIONARY, 3) == bytes((5, 6, 7))

    def test_a_hold_writes_the_value_the_plane_reached(self) -> None:
        stream = bytes((TokenTag.LITERAL | 0, 9, TokenTag.HOLD | 2))
        assert decode_plane(stream, DICTIONARY, 4) == bytes((9, 9, 9, 9))

    def test_a_phrase_writes_the_body_the_table_holds(self) -> None:
        stream = bytes((TokenTag.PHRASE | 0, len(MOTIF) - 1))
        assert decode_plane(stream, DICTIONARY, len(MOTIF)) == MOTIF

    def test_a_phrase_running_past_its_body_holds_the_value_it_ended_on(self) -> None:
        stream = bytes((TokenTag.PHRASE | 0, len(MOTIF) + 1))
        assert decode_plane(stream, DICTIONARY, len(MOTIF) + 2) == MOTIF + bytes((MOTIF[-1],)) * 2

    def test_a_phrase_cut_short_writes_as_much_of_the_body_as_sounded(self) -> None:
        stream = bytes((TokenTag.PHRASE | 0, 1))
        assert decode_plane(stream, DICTIONARY, 2) == MOTIF[:2]

    def test_a_shifted_phrase_writes_the_body_moved_by_the_shift(self) -> None:
        stream = bytes((TokenTag.TRANSPOSED_PHRASE | 0, len(MOTIF) - 1, 5))
        assert decode_plane(stream, DICTIONARY, len(MOTIF)) == bytes(value + 5 for value in MOTIF)

    def test_a_shift_walks_the_byte_around_where_it_reaches_past_one(self) -> None:
        """The driver adds the shift to a byte, so a fall reaches it as the byte that wraps to it."""
        stream = bytes((TokenTag.TRANSPOSED_PHRASE | 0, 0, 0xFD))
        assert decode_plane(stream, DICTIONARY, 1) == bytes((MOTIF[0] - 3,))

    def test_an_escaped_phrase_names_its_id_in_the_byte_that_follows(self) -> None:
        table = phrase_table(
            tuple(Phrase(body=bytes((value, value))) for value in range(PHRASE_ID_ESCAPE)) + (Phrase(body=MOTIF),)
        )
        stream = bytes((TokenTag.PHRASE | PHRASE_ID_ESCAPE, PHRASE_ID_ESCAPE, len(MOTIF) - 1))
        assert decode_plane(stream, table, len(MOTIF)) == MOTIF

    def test_a_token_reaching_past_the_song_stops_where_the_song_does(self) -> None:
        stream = bytes((TokenTag.LITERAL | 0, 4, TokenTag.HOLD | 63))
        assert decode_plane(stream, DICTIONARY, 3) == bytes((4, 4, 4))
