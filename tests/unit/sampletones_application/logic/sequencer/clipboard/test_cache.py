from typing import List, Optional

from sampletones_application.logic.sequencer.clipboard.cache import ParsedBlockCache

BLOCK = "SampleToNES/1 tracker rows=1 slots=3..5"
OTHER = "SampleToNES/1 order rows=1 positions=0..0"


class FakeParser:
    """A parser recording every text it was put to, reading each one as its own length."""

    def __init__(self) -> None:
        self.asked: List[str] = []

    def parse(self, text: str) -> Optional[int]:
        self.asked.append(text)
        return len(text) if text.startswith("SampleToNES") else None


class TestReadingTheSameTextTwice:
    def test_a_text_asked_about_again_is_read_once(self) -> None:
        parser = FakeParser()
        cache: ParsedBlockCache[int] = ParsedBlockCache(parser.parse)

        first = cache.block(BLOCK)
        second = cache.block(BLOCK)

        assert first == second == len(BLOCK)
        assert parser.asked == [BLOCK]

    def test_a_text_reading_as_no_block_is_held_the_same_way(self) -> None:
        """A menu opening over unrelated text costs one comparison, as one over a block does."""
        parser = FakeParser()
        cache: ParsedBlockCache[int] = ParsedBlockCache(parser.parse)

        assert cache.block("a message") is None
        assert cache.block("a message") is None
        assert parser.asked == ["a message"]


class TestReadingAnotherText:
    def test_text_replaced_on_the_clipboard_is_read_afresh(self) -> None:
        parser = FakeParser()
        cache: ParsedBlockCache[int] = ParsedBlockCache(parser.parse)

        cache.block(BLOCK)
        second = cache.block(OTHER)

        assert second == len(OTHER)
        assert parser.asked == [BLOCK, OTHER]

    def test_returning_to_an_earlier_text_reads_it_again(self) -> None:
        parser = FakeParser()
        cache: ParsedBlockCache[int] = ParsedBlockCache(parser.parse)

        cache.block(BLOCK)
        cache.block(OTHER)

        assert cache.block(BLOCK) == len(BLOCK)
        assert parser.asked == [BLOCK, OTHER, BLOCK]
