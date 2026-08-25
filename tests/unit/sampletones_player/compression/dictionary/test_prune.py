from sampletones_player.compression.dictionary.prune import prune
from sampletones_player.compression.dictionary.table import phrase_table
from tests.unit.sampletones_player.compression.dictionary.phrases import phrase


class TestPruningKeepsWhatPaysForItself:
    """A phrase earns its place by sparing more bytes than its own entry takes."""

    def test_a_phrase_no_token_names_is_dropped(self) -> None:
        table = phrase_table((phrase(1, 2), phrase(3, 4)))
        pruned = prune(table, {0: 2, 1: 0}, {0: 100, 1: 100})
        assert pruned.phrases == (phrase(1, 2),)

    def test_a_phrase_sparing_less_than_its_entry_is_dropped(self) -> None:
        table = phrase_table((phrase(1, 2),))
        assert prune(table, {0: 1}, {0: phrase(1, 2).size}).phrases == ()

    def test_the_phrases_named_most_take_the_cheap_ids(self) -> None:
        table = phrase_table((phrase(1, 2), phrase(3, 4)))
        pruned = prune(table, {0: 1, 1: 9}, {0: 100, 1: 100})
        assert pruned.phrases == (phrase(3, 4), phrase(1, 2))
