from typing import Callable, Generic, Optional, TypeVar

BlockT = TypeVar("BlockT")


class ParsedBlockCache(Generic[BlockT]):
    """Holds the block a text last read as, so asking again about it costs one comparison.

    A menu opening asks whether a paste has anything to write and the paste that follows asks
    for the block itself, both about the text standing on the system clipboard, so one parse
    serves every question put about that text.
    """

    def __init__(self, parse: Callable[[str], Optional[BlockT]]) -> None:
        self._parse = parse
        self._text: Optional[str] = None
        self._block: Optional[BlockT] = None

    def block(self, text: str) -> Optional[BlockT]:
        """The block a text reads as, parsed on its first reading and held for the rest."""
        if text != self._text:
            self._text = text
            self._block = self._parse(text)

        return self._block
